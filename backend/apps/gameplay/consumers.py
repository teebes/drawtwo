import asyncio
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Game, GameUpdate
from apps.gameplay.schemas.game import GameState
from apps.gameplay.schemas.updates import GameUpdate as PydGameUpdate
from .services import GameService
from pydantic import TypeAdapter

logger = logging.getLogger(__name__)

# Timeout for channel layer operations (group_add, group_discard, etc.)
# Prevents deadlocks if Redis becomes unresponsive
CHANNEL_LAYER_TIMEOUT = 5.0


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'

        # Check if user is authenticated
        if not self.scope["user"].is_authenticated:
            logger.warning(f"Rejecting unauthenticated WebSocket connection for game {self.game_id}")
            await self.close()
            return

        # Verify user has access to this game and fetch game object
        game = await self.user_can_access_game()
        if not game:
            logger.warning(f"User {self.scope['user']} does not have access to game {self.game_id}")
            await self.close()
            return

        # Determine which side this user is on
        self.side = await self.get_user_side(game)

        # Join the general game group
        # Use timeout to prevent deadlock if Redis is unresponsive
        try:
            await asyncio.wait_for(
                self.channel_layer.group_add(self.game_group_name, self.channel_name),
                timeout=CHANNEL_LAYER_TIMEOUT
            )
            # Join side-specific group for players, spectator group for spectators
            if self.side == 'spectator':
                self.side_group_name = f'game_{self.game_id}_spectator'
            else:
                self.side_group_name = f'game_{self.game_id}_{self.side}'
            await asyncio.wait_for(
                self.channel_layer.group_add(self.side_group_name, self.channel_name),
                timeout=CHANNEL_LAYER_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout joining channel groups for game {self.game_id}")
            await self.close()
            return

        await self.accept()

        # Send current game state using already-fetched game object
        from apps.gameplay.notifications import filter_state_for_side, filter_updates_for_side

        game_state = GameState.model_validate(game.state)
        raw_updates = await self.get_game_updates()
        updates = TypeAdapter(list[PydGameUpdate]).validate_python(raw_updates)

        # Spectators see full state, players see filtered state
        if self.side == 'spectator':
            state_to_send = game_state.model_dump(mode="json")
            updates_to_send = [u.model_dump(mode="json") if hasattr(u, 'model_dump') else u for u in updates]
        else:
            state_to_send = filter_state_for_side(game_state, self.side)
            updates_to_send = filter_updates_for_side(updates, self.side)

        await self.send(text_data=json.dumps({
            'type': 'game_updates',
            'state': state_to_send,
            'updates': updates_to_send,
        }))

        return

    async def disconnect(self, close_code):
        # Leave both groups with timeout to prevent blocking on Redis issues
        try:
            await asyncio.wait_for(
                self.channel_layer.group_discard(self.game_group_name, self.channel_name),
                timeout=CHANNEL_LAYER_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout leaving game group {self.game_group_name}")

        if hasattr(self, 'side_group_name'):
            try:
                await asyncio.wait_for(
                    self.channel_layer.group_discard(self.side_group_name, self.channel_name),
                    timeout=CHANNEL_LAYER_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout leaving side group {self.side_group_name}")

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        logger.debug("#### Consumer received: ####")
        logger.debug(f"received: {data}")

        # Handle heartbeat ping messages (no-op, connection keepalive)
        if message_type == 'ping':
            logger.debug("Received heartbeat ping, responding with pong")
            await self.send(text_data=json.dumps({
                'type': 'pong'
            }))
            return

        # Spectators cannot send game commands
        if self.side == 'spectator':
            logger.warning(f"Spectator {self.scope['user']} attempted to send command to game {self.game_id}")
            await self.send(text_data=json.dumps({
                'type': 'game_updates',
                'state': None,
                'updates': [],
                'errors': [{
                    'type': 'command_validation_error',
                    'reason': 'Spectators cannot take actions in the game',
                    'details': {},
                }],
            }))
            return

        try:
            await self.process_command(data, side=self.side)
        except Exception as e:
            # Handle validation errors and other exceptions gracefully
            error_message = str(e)

            logger.warning(f"Error processing command: {error_message}")

            # Send error back to client in the standard format
            # (same format as errors from effect processing)
            await self.send(text_data=json.dumps({
                'type': 'game_updates',  # Use same type as regular updates
                'state': None,  # No state update
                'updates': [],  # No updates
                'errors': [{
                    'type': 'command_validation_error',
                    'reason': error_message,  # Frontend expects 'reason' field
                    'details': {},
                }],
            }))

    async def game_updates(self, event):
        # Send game updates to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'game_updates',
            'updates': event['updates'],
            'errors': event['errors'],
            'state': event['state']
        }))

    @database_sync_to_async
    def user_can_access_game(self):
        if not self.game_id:
            return None
        try:
            game = Game.objects.get(id=self.game_id)
            user = self.scope["user"]
            # Check if user is a participant in the game (either side)
            # Works for both PvE (one side is user, other is AI) and PvP (both sides are users)
            if game.player_a_user == user or game.player_b_user == user:
                return game
            # Staff/superuser can view any game as spectator (read-only)
            if user.is_staff or user.is_superuser:
                return game
            return None
        except Game.DoesNotExist:
            return None

    @database_sync_to_async
    def get_user_side(self, game):
        """
        Determine which side of the game this user is on.
        Returns 'side_a', 'side_b', or 'spectator' for staff viewing others' games.
        """
        user = self.scope["user"]

        # Check if user owns side_a's deck
        if game.player_a_user == user:
            return 'side_a'
        # Check if user owns side_b's deck
        elif game.player_b_user == user:
            return 'side_b'
        # If AI game, assign human player to their side
        elif game.side_a.is_ai_deck:
            return 'side_b'  # User is on side_b, AI on side_a
        elif game.side_b.is_ai_deck:
            return 'side_a'  # User is on side_a, AI on side_b
        # Staff/superuser viewing others' game as spectator
        elif user.is_staff or user.is_superuser:
            return 'spectator'
        else:
            # Default to side_a if we can't determine
            return 'side_a'

    @database_sync_to_async
    def get_game_updates(self):
        # Evaluate queryset in sync context and return list of raw update dicts
        return list(
            GameUpdate.objects
            .filter(game_id=self.game_id)
            .order_by('created_at')
            .values_list('update', flat=True)
        )

    @database_sync_to_async
    def process_command(self, command, side):
        return GameService.process_command(
            game_id=self.game_id,
            command=command,
            side=side,
        )

    @database_sync_to_async
    def process_game_action(self, action):
        return GameService.submit_action(
            game_id=self.game_id,
            action=action,
        )


class UserConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user-level notifications (matchmaking, friend requests, etc.).
    Each authenticated user connects to their own channel for real-time updates.
    """

    async def connect(self):
        # Check if user is authenticated
        if not self.scope["user"].is_authenticated:
            logger.warning("Rejecting unauthenticated WebSocket connection for user channel")
            await self.close()
            return

        self.user_id = self.scope["user"].id
        self.user_group_name = f'user_{self.user_id}'

        # Join user-specific group with timeout
        try:
            await asyncio.wait_for(
                self.channel_layer.group_add(self.user_group_name, self.channel_name),
                timeout=CHANNEL_LAYER_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout joining user channel group for user {self.user_id}")
            await self.close()
            return

        await self.accept()
        logger.info(f"User {self.user_id} connected to user channel")

    async def disconnect(self, close_code):
        # Leave user group with timeout
        if hasattr(self, 'user_group_name'):
            try:
                await asyncio.wait_for(
                    self.channel_layer.group_discard(self.user_group_name, self.channel_name),
                    timeout=CHANNEL_LAYER_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout leaving user group {self.user_group_name}")
            logger.info(f"User {self.user_id} disconnected from user channel")

    async def matchmaking_success(self, event):
        """
        Handle matchmaking success notification.
        Sends game_id and title_slug to frontend so it can navigate to the game.
        """
        await self.send(text_data=json.dumps({
            'type': 'matchmaking_success',
            'game_id': event['game_id'],
            'title_slug': event['title_slug'],
        }))
        logger.info(f"Sent matchmaking success to user {self.user_id} for game {event['game_id']}")
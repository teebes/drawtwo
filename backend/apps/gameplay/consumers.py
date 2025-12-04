import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Game, GameUpdate
#from .schemas import GameState, GameUpdate as PydGameUpdate
from apps.gameplay.schemas.game import GameState
from apps.gameplay.schemas.updates import GameUpdate as PydGameUpdate
from .services import GameService
from pydantic import TypeAdapter

logger = logging.getLogger(__name__)


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
        self.side_group_name = f'game_{self.game_id}_{self.side}'

        # Join both the general game group and the side-specific group
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )
        await self.channel_layer.group_add(
            self.side_group_name,
            self.channel_name
        )

        await self.accept()

        # Send current game state using already-fetched game object
        # Filter the state for this player's side
        from apps.gameplay.notifications import filter_state_for_side, filter_updates_for_side

        game_state = GameState.model_validate(game.state)
        filtered_state = filter_state_for_side(game_state, self.side)

        raw_updates = await self.get_game_updates()
        updates = TypeAdapter(list[PydGameUpdate]).validate_python(raw_updates)
        filtered_updates = filter_updates_for_side(updates, self.side)

        await self.send(text_data=json.dumps({
            'type': 'game_updates',
            'state': filtered_state,
            'updates': filtered_updates,
        }))

        return

    async def disconnect(self, close_code):
        # Leave both groups
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )
        if hasattr(self, 'side_group_name'):
            await self.channel_layer.group_discard(
                self.side_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        logger.debug("#### Consumer received: ####")
        logger.debug(f"received: {data}")

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
            return None
        except Game.DoesNotExist:
            return None

    @database_sync_to_async
    def get_user_side(self, game):
        """
        Determine which side of the game this user is on.
        Returns 'side_a' or 'side_b'.
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

        # Join user-specific group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"User {self.user_id} connected to user channel")

    async def disconnect(self, close_code):
        # Leave user group
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
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
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Game, GameUpdate
from .schemas import GameState, GameUpdates, GameUpdate as PydGameUpdate
from .services import GameService
from pydantic import TypeAdapter


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'

        # Check if user is authenticated
        if not self.scope["user"].is_authenticated:
            await self.close()
            return

        # Verify user has access to this game and fetch game object
        game = await self.user_can_access_game()
        if not game:
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

        print("#### Consumer received: ####")
        print(f"received: {data}")

        try:
            await self.process_command(data, side=self.side)
        except Exception as e:
            # Handle validation errors and other exceptions gracefully
            error_message = str(e)

            print(f"Error processing command: {error_message}")

            # Send error back to client
            await self.send(text_data=json.dumps({
                'type': 'command_error',
                'errors': [{'message': error_message}],
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
            # Check if user is part of the game
            if (game.side_a.user == user or game.side_b.user == user or
                    game.side_a.ai_player is not None or game.side_b.ai_player is not None):
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
        if game.side_a.user == user:
            return 'side_a'
        # Check if user owns side_b's deck
        elif game.side_b.user == user:
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
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

        # Verify user has access to this game
        if not await self.user_can_access_game():
            await self.close()
            return

        # Join game group
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )

        await self.accept()

        # Send current game state
        game_state = await self.get_game_state()

        raw_updates = await self.get_game_updates()
        updates = TypeAdapter(list[PydGameUpdate]).validate_python(raw_updates)

        await self.send(text_data=json.dumps(
            GameUpdates(
                state=GameState.model_validate(game_state),
                updates=updates,
            ).model_dump(mode="json")
        ))

        return

    async def disconnect(self, close_code):
        # Leave game group
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        print("#########################")
        print(f"received: {data}")
        print("#########################")

        result = await self.process_game_action(data)

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
            return False
        try:
            game = Game.objects.get(id=self.game_id)
            user = self.scope["user"]
            # Check if user is part of the game
            return (game.side_a.user == user or game.side_b.user == user or
                    game.side_a.ai_player is not None or game.side_b.ai_player is not None)
        except Game.DoesNotExist:
            return False

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
    def get_game_state(self):
        game = Game.objects.get(id=self.game_id)
        return game.state

    @database_sync_to_async
    def process_game_action(self, action):

        return GameService.submit_action(
            game_id=self.game_id,
            action=action,
        )
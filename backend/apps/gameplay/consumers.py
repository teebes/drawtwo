import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Game
from .engine import apply_action
from .schemas import GameState, GameUpdates
from .services import GameService


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'

        # Check if user is authenticated
        if self.scope["user"] == AnonymousUser():
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
        await self.send(text_data=json.dumps(
            GameUpdates(
                state=GameState.model_validate(game_state),
                updates=[],
            ).model_dump()
        ))

        return
        await self.send(text_data=json.dumps({
            'type': 'game_state',
            'state': game_state
        }))

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

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'game_updates',
                'updates': result['updates'],
                'state': result['state']
            }
        )

        return

        if message_type == 'action':
            # Handle game action
            action = data.get('action')
            if action:
                print(f"Processing action: {action}")
                result = await self.process_game_action(action)
                print(f"Action result: {result}")

                # Broadcast update to all players in the game
                await self.channel_layer.group_send(
                    self.game_group_name,
                    {
                        'type': 'game_update',
                        'update': result
                    }
                )
    """
    async def game_update(self, event):
        # Send game update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'game_update',
            'update': event['update']
        }))
    """

    async def game_updates(self, event):
        # Send game updates to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'game_updates',
            'updates': event['updates'],
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
    def get_game_state(self):
        game = Game.objects.get(id=self.game_id)
        return game.state

    @database_sync_to_async
    def process_game_action(self, action):

        return GameService.submit_action(
            game_id=self.game_id,
            action=action,
        )

        game = Game.objects.get(id=self.game_id)

        # Parse current state to get active player
        current_state = GameState.model_validate(game.state)

        # Add player field if not present
        if 'player' not in action:
            action['player'] = current_state.active

        # Apply action to game state
        new_state = apply_action(game.state, action)
        game.state = json.loads(new_state)
        game.save()

        # Parse the state to check for specific updates
        state = GameState.model_validate(game.state)

        # Determine what type of update this is
        update_type = 'state_change'

        # Check if a card was drawn
        if action.get('type') == 'phase_transition' and state.phase == 'draw':
            update_type = 'draw_card'

        return {
            'type': update_type,
            'state': game.state,
            'action': action
        }
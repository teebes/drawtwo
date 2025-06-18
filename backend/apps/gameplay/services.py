from django.db import transaction
from .models import Game
from .schemas import GameState
from .tasks import process_player_action


class GameService:

    @staticmethod
    @transaction.atomic
    def start_game(deck_a, deck_b) -> Game:
        state = GameState.model_dump_json()
        game = Game.objects.create(
            side_a=deck_a,
            side_b=deck_b,
            status=Game.GAME_STATUS_INIT,
            state=state,
        )
        process_player_action.delay(game.id, {"type": "noop"})
        return game

    @staticmethod
    def submit_action(game_id: int, action: dict):
        process_player_action.delay(game_id, action)

from celery import shared_task
from django.db import transaction


from .models import Game
from .schemas import GameState

@shared_task
def process_player_action(game_id: int, action: dict):
    with transaction.atomic():
        game = (Game.objects
                    .select_for_update()
                    .get(id=game_id))

        new_state_dict, emitted = apply_action(game.state, action)

        new_state = GameState.model_validate(new_state_dict)
        game.state = new_state_dict
        game.statue = Game.GAME_STATUS_IN_PROGRESS
        game.winner = new_state_dict.get("winner")
        game.save(update_fields=["state", "status", "winner"])

    # TODO: push_ws_to_clients(game_id, action, emitted)
from celery import shared_task
from apps.gameplay.services import GameService

@shared_task
def advance(game_id: int):
    return GameService.advance(game_id)
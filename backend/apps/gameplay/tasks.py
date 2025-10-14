from celery import shared_task
from apps.gameplay.services import GameService

@shared_task
def step(game_id: int):
    return GameService.step(game_id)
from celery import shared_task
from apps.gameplay.services import GameService

@shared_task
def step(game_id: int):
    return GameService.step(game_id)

@shared_task
def process_matchmaking(title_id: int, ladder_type: str = None):
    """
    Process matchmaking queue for a specific title.
    Attempts to find and match players with similar ELO ratings.
    """
    if ladder_type is None:
        return GameService.process_matchmaking(title_id)
    return GameService.process_matchmaking(title_id, ladder_type=ladder_type)

@shared_task
def check_expired_turns():
    """
    Periodic task to check for expired turns in active games.
    Runs every 5 seconds to catch timeouts even when no effects are being processed.
    """
    return GameService.check_expired_turns()

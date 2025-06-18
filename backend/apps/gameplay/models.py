from django.db import models

from apps.collection.models import Deck
from apps.core.models import TimestampedModel, list_to_choices


class Game(TimestampedModel):
    TURN_PHASE_START = 'start'
    TURN_PHASE_REFRSH = 'refresh'
    TURN_PHASE_DRAW = 'draw'
    TURN_PHASE_MAIN = 'main'
    TURN_PHASE_COMBAT = 'combat'
    TURN_PHASE_END = 'end'

    GAME_STATUS_INIT = 'init'
    GAME_STATUS_IN_PROGRESS = 'in_progress'
    GAME_STATUS_ENDED = 'ended'

    status = models.CharField(
        max_length=20,
        choices=list_to_choices(
            [GAME_STATUS_INIT, GAME_STATUS_IN_PROGRESS, GAME_STATUS_ENDED]
        ),
        default=GAME_STATUS_INIT,
    )
    side_a = models.ForeignKey(Deck, on_delete=models.PROTECT, related_name='games_as_side_a')
    side_b = models.ForeignKey(Deck, on_delete=models.PROTECT, related_name='games_as_side_b')

    state = models.JSONField(default=dict)

    """
    current_turn = models.ForeignKey(Deck, on_delete=models.PROTECT,
                                     blank=True, null=True)
    turn_counter = models.SmallIntegerField(default=0)

    phase = models.CharField(
        max_length=10,
        choices=list_to_choices(
            [
                TURN_PHASE_START,
                TURN_PHASE_REFRSH,
                TURN_PHASE_DRAW,
                TURN_PHASE_MAIN,
                TURN_PHASE_COMBAT,
                TURN_PHASE_END]
        ),
        default=TURN_PHASE_START,
    )
    """

    winner = models.ForeignKey(Deck, on_delete=models.PROTECT,
                               blank=True, null=True, related_name='games_won')

    def __str__(self):
        return f"{self.side_a.name} vs {self.side_b.name}"

from django.db import models

from apps.collection.models import Deck
from apps.core.models import TimestampedModel, list_to_choices
from .schemas import GameEvent, GameState


class Game(TimestampedModel):

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

    winner = models.ForeignKey(Deck, on_delete=models.PROTECT,
                               blank=True, null=True, related_name='games_won')

    @property
    def game_state(self):
        return GameState.model_validate(self.state)

    @property
    def is_vs_ai(self):
        """Returns True if this is a player vs AI game"""
        return self.side_a.is_ai_deck or self.side_b.is_ai_deck

    @property
    def human_deck(self):
        """Returns the human player's deck (assumes only one AI)"""
        if self.side_a.is_ai_deck:
            return self.side_b
        elif self.side_b.is_ai_deck:
            return self.side_a
        return None  # Both human

    @property
    def ai_deck(self):
        """Returns the AI player's deck (assumes only one AI)"""
        if self.side_a.is_ai_deck:
            return self.side_a
        elif self.side_b.is_ai_deck:
            return self.side_b
        return None  # No AI

    def push_event(self, event: GameEvent):
        state = GameState.model_validate(self.state)
        state.event_queue.append(event)
        self.state = state.model_dump()
        self.save(update_fields=["state"])

    def __str__(self):
        return f"{self.side_a.name} vs {self.side_b.name}"

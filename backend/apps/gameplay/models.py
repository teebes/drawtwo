from django.contrib.auth import get_user_model
from django.db import models

from apps.collection.models import Deck
from apps.core.models import TimestampedModel, list_to_choices
from apps.gameplay.schemas.game import GameState
from apps.gameplay.schemas.effects import Effect

User = get_user_model()


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

    queue = models.JSONField(default=list)

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

    @property
    def title(self):
        """Returns the title this game is for (both decks must be same title)"""
        return self.side_a.title

    def __str__(self):
        return f"{self.side_a.name} vs {self.side_b.name}"

    def enqueue(self, effects: list[Effect], trigger: bool=True, prepend: bool=False):
        if effects:
            serialized_effects = [effect.model_dump() for effect in effects]
            if prepend:
                self.queue = serialized_effects + self.queue
            else:
                self.queue.extend(serialized_effects)
            self.save(update_fields=['queue'])
        if trigger:
            from apps.gameplay.tasks import step
            step.apply_async(args=[self.id])


class GameUpdate(TimestampedModel):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    update = models.JSONField()

    def __str__(self):
        return f"{self.game.side_a.name} vs {self.game.side_b.name} - {self.update['type']}"


class UserTitleRating(TimestampedModel):
    """
    Tracks a user's ELO rating for a specific title.
    Each user has a separate rating for each title they play.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='title_ratings'
    )
    title = models.ForeignKey(
        'builder.Title',
        on_delete=models.CASCADE,
        related_name='user_ratings'
    )
    elo_rating = models.IntegerField(
        default=1200,
        help_text="Player's ELO rating for this title (default: 1200)"
    )

    class Meta:
        db_table = 'gameplay_user_title_rating'
        verbose_name = 'User Title Rating'
        verbose_name_plural = 'User Title Ratings'
        unique_together = [['user', 'title']]
        indexes = [
            models.Index(fields=['title', '-elo_rating']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.display_name} - {self.title.name}: {self.elo_rating}"


class ELORatingChange(TimestampedModel):
    """
    Tracks ELO rating changes for PvP matches.
    Only created for human vs human games (not vs AI).
    """
    game = models.OneToOneField(
        Game,
        on_delete=models.CASCADE,
        related_name='elo_change'
    )

    title = models.ForeignKey(
        'builder.Title',
        on_delete=models.CASCADE,
        related_name='elo_changes',
        help_text="The title this rating change is for",
        null=True,  # Temporarily nullable for migration
        blank=True
    )

    # Winner's rating change
    winner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='elo_wins'
    )
    winner_old_rating = models.IntegerField()
    winner_new_rating = models.IntegerField()
    winner_rating_change = models.IntegerField()

    # Loser's rating change
    loser = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='elo_losses'
    )
    loser_old_rating = models.IntegerField()
    loser_new_rating = models.IntegerField()
    loser_rating_change = models.IntegerField()

    class Meta:
        db_table = 'gameplay_elo_rating_change'
        verbose_name = 'ELO Rating Change'
        verbose_name_plural = 'ELO Rating Changes'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['winner']),
            models.Index(fields=['loser']),
            models.Index(fields=['title']),
        ]

    def __str__(self):
        return (
            f"{self.title.name}: {self.winner.display_name} ({self.winner_rating_change:+d}) "
            f"vs {self.loser.display_name} ({self.loser_rating_change:+d})"
        )

from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import Q, Case, When, Value

from apps.collection.models import Deck
from apps.core.models import TimestampedModel, list_to_choices
from apps.gameplay.schemas.game import GameState
from apps.gameplay.schemas.effects import Effect

User = get_user_model()


class GameQuerySet(models.QuerySet):
    """Custom QuerySet for Game with title-scoped query methods."""

    def for_title(self, title):
        """Filter games for a specific title. All queries should start here."""
        return self.filter(title=title)

    def for_user(self, user):
        """Filter games where user is a participant. Must be chained after for_title."""
        return self.filter(Q(player_a_user=user) | Q(player_b_user=user))

    def pve_for_user(self, title, user):
        """Convenience method: PvE games for a user in a title."""
        return self.for_title(title).for_user(user).filter(type='pve')

    def ranked_for_user(self, title, user):
        """Convenience method: Ranked games for a user in a title."""
        return self.for_title(title).for_user(user).filter(type='ranked')

    def friendly_for_user(self, title, user):
        """Convenience method: Friendly games for a user in a title."""
        return self.for_title(title).for_user(user).filter(type='friendly')

    def where_user_is_side(self, title, user):
        """Get games with annotation showing which side user is on."""
        return self.for_title(title).for_user(user).annotate(
            user_side=Case(
                When(player_a_user=user, then=Value('side_a')),
                When(player_b_user=user, then=Value('side_b')),
            )
        )


class Game(TimestampedModel):

    GAME_STATUS_INIT = 'init'
    GAME_STATUS_IN_PROGRESS = 'in_progress'
    GAME_STATUS_ENDED = 'ended'

    GAME_TYPE_PVE = 'pve'
    GAME_TYPE_RANKED = 'ranked'
    GAME_TYPE_FRIENDLY = 'friendly'

    LADDER_TYPE_RAPID = 'rapid'
    LADDER_TYPE_DAILY = 'daily'

    LADDER_TYPE_CHOICES = list_to_choices([LADDER_TYPE_RAPID, LADDER_TYPE_DAILY])

    type = models.CharField(
        max_length=20,
        choices=list_to_choices([GAME_TYPE_PVE, GAME_TYPE_RANKED, GAME_TYPE_FRIENDLY]),
        default=GAME_TYPE_PVE,
    )

    ladder_type = models.CharField(
        max_length=20,
        choices=LADDER_TYPE_CHOICES,
        null=True,
        blank=True,
        help_text="Ladder type for ranked games (rapid or daily).",
    )

    status = models.CharField(
        max_length=20,
        choices=list_to_choices(
            [GAME_STATUS_INIT, GAME_STATUS_IN_PROGRESS, GAME_STATUS_ENDED]
        ),
        default=GAME_STATUS_INIT,
    )
    side_a = models.ForeignKey(Deck, on_delete=models.PROTECT, related_name='games_as_side_a')
    side_b = models.ForeignKey(Deck, on_delete=models.PROTECT, related_name='games_as_side_b')

    # Denormalized fields for easier querying
    title = models.ForeignKey(
        'builder.Title',
        on_delete=models.PROTECT,
        related_name='games',
        help_text="The title this game is for (denormalized from side_a.title)"
    )
    player_a_user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='games_as_player_a',
        null=True,
        blank=True,
        help_text="User on side_a (denormalized from side_a.user)"
    )
    player_b_user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='games_as_player_b',
        null=True,
        blank=True,
        help_text="User on side_b (denormalized from side_b.user)"
    )

    state = models.JSONField(default=dict)

    objects = GameQuerySet.as_manager()

    winner = models.ForeignKey(Deck, on_delete=models.PROTECT,
                               blank=True, null=True, related_name='games_won')

    queue = models.JSONField(default=list)

    # Time control fields
    turn_expires = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the current turn expires (for time enforcement)"
    )

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

    def opponent_deck_for_user(self, user):
        if self.side_a.user == user:
            return self.side_b
        elif self.side_b.user == user:
            return self.side_a
        return None

    def __str__(self):
        return f"{self.side_a.name} vs {self.side_b.name}"

    def save(self, *args, **kwargs):
        """Auto-populate denormalized fields from side_a and side_b."""
        # Only populate if side_a and side_b are set
        if self.side_a_id:
            # Title is same for both sides (validated elsewhere)
            if not self.title_id:
                self.title = self.side_a.title
            self.player_a_user = self.side_a.user
        if self.side_b_id:
            self.player_b_user = self.side_b.user
        super().save(*args, **kwargs)

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
            # Ensure the transaction is committed before triggering the step task
            # This prevents the step task from failing silently due to lock contention
            transaction.on_commit(lambda: step.apply_async(args=[self.id]))


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
    ladder_type = models.CharField(
        max_length=20,
        choices=Game.LADDER_TYPE_CHOICES,
        default=Game.LADDER_TYPE_RAPID,
        help_text="Which ladder this rating applies to."
    )
    elo_rating = models.IntegerField(
        default=1200,
        help_text="Player's ELO rating for this title (default: 1200)"
    )

    class Meta:
        db_table = 'gameplay_user_title_rating'
        verbose_name = 'User Title Rating'
        verbose_name_plural = 'User Title Ratings'
        unique_together = [['user', 'title', 'ladder_type']]
        indexes = [
            models.Index(fields=['title', 'ladder_type', '-elo_rating']),
            models.Index(fields=['user', 'ladder_type']),
        ]

    def __str__(self):
        return f"{self.user.display_name} - {self.title.name} ({self.ladder_type}): {self.elo_rating}"


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
    ladder_type = models.CharField(
        max_length=20,
        choices=Game.LADDER_TYPE_CHOICES,
        default=Game.LADDER_TYPE_RAPID,
        help_text="Which ladder this rating change applies to."
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
            models.Index(fields=['title', 'ladder_type']),
        ]

    def __str__(self):
        return (
            f"{self.title.name} ({self.ladder_type}): "
            f"{self.winner.display_name} ({self.winner_rating_change:+d}) "
            f"vs {self.loser.display_name} ({self.loser_rating_change:+d})"
        )


class MatchmakingQueue(TimestampedModel):
    """
    Tracks players queuing for ranked matchmaking.
    Players are matched based on their ELO rating and queue time.
    """
    STATUS_QUEUED = 'queued'
    STATUS_MATCHED = 'matched'
    STATUS_CANCELLED = 'cancelled'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='matchmaking_queue_entries',
        help_text="The user queuing for a match"
    )

    deck = models.ForeignKey(
        Deck,
        on_delete=models.CASCADE,
        related_name='matchmaking_queue_entries',
        help_text="The deck the user will use for the match"
    )

    ladder_type = models.CharField(
        max_length=20,
        choices=Game.LADDER_TYPE_CHOICES,
        default=Game.LADDER_TYPE_RAPID,
        help_text="Which ladder this queue entry is for."
    )

    status = models.CharField(
        max_length=20,
        choices=list_to_choices([STATUS_QUEUED, STATUS_MATCHED, STATUS_CANCELLED]),
        default=STATUS_QUEUED,
        help_text="Current status of the queue entry"
    )

    elo_rating = models.IntegerField(
        help_text="User's ELO rating at the time of queueing (for matchmaking)"
    )

    matched_with = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='match_partner',
        help_text="The queue entry this user was matched with"
    )

    game = models.ForeignKey(
        Game,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matchmaking_queue_entries',
        help_text="The game created from this matchmaking"
    )

    class Meta:
        db_table = 'gameplay_matchmaking_queue'
        verbose_name = 'Matchmaking Queue Entry'
        verbose_name_plural = 'Matchmaking Queue Entries'
        indexes = [
            models.Index(fields=['status', 'ladder_type', 'elo_rating']),
            models.Index(fields=['user', 'status', 'ladder_type']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        title = getattr(self.deck, 'title', None)
        title_name = getattr(title, 'name', 'Unknown Title')
        return f"{self.user.display_name} - {title_name} ({self.ladder_type}, {self.status})"

    @property
    def title(self):
        """
        Convenience accessor to the queue entry's title.
        Ensures existing matchmaking logic can reference entry.title
        without needing a separate DB column.
        """
        return getattr(self.deck, 'title', None)


class FriendlyChallenge(TimestampedModel):
    """
    Represents a direct friend-vs-friend challenge request.
    When accepted, a Game is created and marked as unrated.
    """
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_CANCELLED = 'cancelled'
    STATUS_EXPIRED = 'expired'

    status = models.CharField(
        max_length=20,
        choices=list_to_choices([STATUS_PENDING, STATUS_ACCEPTED, STATUS_CANCELLED, STATUS_EXPIRED]),
        default=STATUS_PENDING
    )

    challenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenges_sent')
    challengee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenges_received')

    title = models.ForeignKey('builder.Title', on_delete=models.CASCADE, related_name='friendly_challenges')

    challenger_deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='as_challenger_in_challenges')
    challengee_deck = models.ForeignKey(Deck, on_delete=models.CASCADE, null=True, blank=True, related_name='as_challengee_in_challenges')

    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True, blank=True, related_name='friendly_challenge')

    class Meta:
        db_table = 'gameplay_friendly_challenge'
        indexes = [
            models.Index(fields=['status', 'title']),
            models.Index(fields=['challenger', 'challengee', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(challenger=models.F('challengee')),
                name='friendly_challenge_no_self'
            ),
        ]

    def __str__(self):
        return f"{self.challenger.display_name} -> {self.challengee.display_name} [{self.title.name}] ({self.status})"


class PlayerNotification(TimestampedModel):
    """
    Game-related notifications for players to be displayed in the Title Lobby,
    for example that a game has started or ended.

    * Game challenge
    * Game started
    * Game ended
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gameplay_player_notification'
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

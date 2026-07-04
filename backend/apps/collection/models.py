from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from apps.builder.models import AIPlayer, CardTemplate, HeroTemplate, Title
from apps.core.models import TimestampedModel

User = get_user_model()


class OwnedCard(TimestampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card = models.ForeignKey(CardTemplate, on_delete=models.PROTECT)
    count = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "card"],
                name="owned_card_u_user_card",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} → {self.card.name} ({self.count})"


class OwnedHero(TimestampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    hero = models.ForeignKey(HeroTemplate, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "hero"],
                name="owned_hero_u_user_hero",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} → {self.hero.name}"


class DeckQuerySet(models.QuerySet):
    def active(self):
        return self.filter(archived_at__isnull=True)

    def archived(self):
        return self.filter(archived_at__isnull=False)


class Deck(TimestampedModel):
    # Either user-owned or AI-owned (exactly one must be set)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ai_player = models.ForeignKey(
        AIPlayer, on_delete=models.CASCADE, null=True, blank=True
    )

    # Title that this deck belongs to
    title = models.ForeignKey(Title, on_delete=models.PROTECT)

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cards = models.ManyToManyField(CardTemplate, through="DeckCard")
    hero = models.ForeignKey(HeroTemplate, on_delete=models.PROTECT)

    script = models.JSONField(default=dict, blank=True)
    is_pve_opponent = models.BooleanField(
        default=True,
        help_text="Whether this AI deck appears in normal PvE opponent selection.",
    )
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = DeckQuerySet.as_manager()

    class Meta:
        constraints = [
            # Ensure exactly one owner
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False, ai_player__isnull=True)
                    | models.Q(user__isnull=True, ai_player__isnull=False)
                ),
                name="deck_exactly_one_owner",
            ),
            # Unique name per user
            models.UniqueConstraint(
                fields=["user", "name"],
                condition=models.Q(user__isnull=False, archived_at__isnull=True),
                name="deck_u_user_name",
            ),
            # Unique name per AI player
            models.UniqueConstraint(
                fields=["ai_player", "name"],
                condition=models.Q(ai_player__isnull=False, archived_at__isnull=True),
                name="deck_u_ai_name",
            ),
        ]

    @property
    def owner(self):
        """Returns the owner (User or AIPlayer)"""
        return self.user or self.ai_player

    @property
    def owner_name(self):
        """Returns displayable owner name"""
        if self.user:
            return self.user.display_name
        return f"🤖 {self.ai_player.name}"

    @property
    def is_ai_deck(self):
        """Returns True if this is an AI-owned deck"""
        return self.ai_player is not None

    @property
    def is_archived(self):
        return self.archived_at is not None

    def archive(self, when=None):
        if self.archived_at:
            return False

        when = when or timezone.now()
        self.archived_at = when
        self.updated_at = when
        self.save(update_fields=["archived_at", "updated_at"])
        return True

    @property
    def deck_size(self):
        """
        Returns the total number of cards in the deck, counting duplicates.
        """
        return self.deckcard_set.aggregate(total=models.Sum("count"))["total"] or 0

    def __str__(self):
        return f"{self.owner_name} → {self.name}"


class UserTitleDeckPreference(TimestampedModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="deck_preferences"
    )
    title = models.ForeignKey(
        Title, on_delete=models.CASCADE, related_name="deck_preferences"
    )
    last_used_deck = models.ForeignKey(
        Deck, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    last_used_friend = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "title"], name="user_title_deck_preference_unique"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "title"]),
        ]

    def __str__(self):
        return f"{self.user.display_name} → {self.title.name}"


class DeckCard(TimestampedModel):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE)
    card = models.ForeignKey(CardTemplate, on_delete=models.PROTECT)
    count = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deck", "card"],
                name="deck_card_u_deck_card",
            ),
        ]

    def __str__(self):
        return f"{self.deck.name} → {self.card.name} ({self.count})"

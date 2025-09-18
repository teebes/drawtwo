from django.contrib.auth import get_user_model
from django.db import models

from apps.core.models import TimestampedModel
from apps.builder.models import CardTemplate, HeroTemplate, AIPlayer, Title

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


class Deck(TimestampedModel):
    # Either user-owned or AI-owned (exactly one must be set)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ai_player = models.ForeignKey(AIPlayer, on_delete=models.CASCADE, null=True, blank=True)

    # Title that this deck belongs to
    title = models.ForeignKey(Title, on_delete=models.PROTECT)

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cards = models.ManyToManyField(CardTemplate, through='DeckCard')
    hero = models.ForeignKey(HeroTemplate, on_delete=models.PROTECT)

    script = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            # Ensure exactly one owner
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False, ai_player__isnull=True) |
                    models.Q(user__isnull=True, ai_player__isnull=False)
                ),
                name='deck_exactly_one_owner'
            ),
            # Unique name per user
            models.UniqueConstraint(
                fields=["user", "name"],
                condition=models.Q(user__isnull=False),
                name="deck_u_user_name",
            ),
            # Unique name per AI player
            models.UniqueConstraint(
                fields=["ai_player", "name"],
                condition=models.Q(ai_player__isnull=False),
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
            return self.user.email
        return f"🤖 {self.ai_player.name}"

    @property
    def is_ai_deck(self):
        """Returns True if this is an AI-owned deck"""
        return self.ai_player is not None

    @property
    def deck_size(self):
        """
        Returns the total number of cards in the deck, counting duplicates.
        """
        return self.deckcard_set.aggregate(
            total=models.Sum('count')
        )['total'] or 0

    def __str__(self):
        return f"{self.owner_name} → {self.name}"


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

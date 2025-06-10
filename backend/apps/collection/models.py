from django.contrib.auth import get_user_model
from django.db import models

from apps.core.models import TimestampedModel
from apps.builder.models import CardTemplate, HeroTemplate

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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cards = models.ManyToManyField(CardTemplate, through='DeckCard')
    hero = models.ForeignKey(HeroTemplate, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="deck_u_user_name",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} → {self.name}"


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

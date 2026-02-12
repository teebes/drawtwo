from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.builder.models import AIPlayer, CardTemplate, HeroTemplate, Title
from apps.collection.models import Deck, DeckCard

User = get_user_model()


class DeckMinimumCardsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="user@example.com", username="user")
        self.ai_player = AIPlayer.objects.create(name="AI")

        self.title = Title.objects.create(
            slug="deck-min-title",
            name="Deck Min Title",
            author=self.user,
            config={"min_cards_in_deck": 10},
        )

        self.hero_user = HeroTemplate.objects.create(
            title=self.title,
            slug="hero-user",
            name="Hero User",
            health=10,
        )
        self.hero_ai = HeroTemplate.objects.create(
            title=self.title,
            slug="hero-ai",
            name="Hero AI",
            health=10,
        )

        self.player_deck = Deck.objects.create(
            title=self.title,
            user=self.user,
            name="Player Deck",
            hero=self.hero_user,
        )
        self.ai_deck = Deck.objects.create(
            title=self.title,
            ai_player=self.ai_player,
            name="AI Deck",
            hero=self.hero_ai,
        )

        cards = []
        for i in range(10):
            cards.append(
                CardTemplate.objects.create(
                    title=self.title,
                    slug=f"min-card-{i}",
                    name=f"Min Card {i}",
                    cost=1,
                )
            )

        for card in cards[:4]:
            DeckCard.objects.create(deck=self.player_deck, card=card, count=1)
        for card in cards:
            DeckCard.objects.create(deck=self.ai_deck, card=card, count=1)

        self.client.force_authenticate(self.user)

    def test_queue_rejects_deck_below_minimum(self):
        response = self.client.post(
            reverse("queue-ranked-match"),
            {"deck_id": self.player_deck.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("at least 10 cards", response.json()["error"])

    def test_game_create_rejects_player_deck_below_minimum(self):
        response = self.client.post(
            reverse("game-create"),
            {
                "player_deck_id": self.player_deck.id,
                "ai_deck_id": self.ai_deck.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn(
            "Player deck must have at least 10 cards", response.json()["error"]
        )

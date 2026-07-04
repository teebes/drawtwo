from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.builder.models import AIPlayer, CardTemplate, CardTrait, HeroTemplate, Title
from apps.collection.models import Deck, DeckCard
from apps.gameplay.models import Game, MatchmakingQueue
from apps.gameplay.services import GameService

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

    def test_queue_rejects_archived_deck(self):
        self.player_deck.archive()

        response = self.client.post(
            reverse("queue-ranked-match"),
            {"deck_id": self.player_deck.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("archived", response.json()["error"])

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

    def test_game_create_rejects_archived_player_deck(self):
        self.player_deck.archive()

        response = self.client.post(
            reverse("game-create"),
            {
                "player_deck_id": self.player_deck.id,
                "ai_deck_id": self.ai_deck.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("Player deck has been archived", response.json()["error"])

    def test_queue_rejects_deck_above_maximum(self):
        self.title.config = {
            "min_cards_in_deck": 1,
            "deck_size_limit": 3,
            "deck_card_max_count": 9,
        }
        self.title.save(update_fields=["config"])

        response = self.client.post(
            reverse("queue-ranked-match"),
            {"deck_id": self.player_deck.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("cannot have more than 3 cards", response.json()["error"])

    def test_game_create_rejects_deck_above_maximum(self):
        self.title.config = {
            "min_cards_in_deck": 1,
            "deck_size_limit": 3,
            "deck_card_max_count": 9,
        }
        self.title.save(update_fields=["config"])

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
            "Player deck cannot have more than 3 cards", response.json()["error"]
        )

    def test_queue_rejects_deck_above_copy_limit(self):
        self.title.config = {
            "min_cards_in_deck": 1,
            "deck_size_limit": 30,
            "deck_card_max_count": 1,
        }
        self.title.save(update_fields=["config"])
        deck_card = self.player_deck.deckcard_set.first()
        deck_card.count = 2
        deck_card.save(update_fields=["count"])

        response = self.client.post(
            reverse("queue-ranked-match"),
            {"deck_id": self.player_deck.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("cannot have more than 1 copy", response.json()["error"])

    def test_queue_rejects_deck_when_card_becomes_unique(self):
        self.title.config = {
            "min_cards_in_deck": 1,
            "deck_size_limit": 30,
            "deck_card_max_count": 9,
        }
        self.title.save(update_fields=["config"])
        deck_card = self.player_deck.deckcard_set.first()
        deck_card.count = 2
        deck_card.save(update_fields=["count"])
        CardTrait.objects.create(card=deck_card.card, trait_slug="unique")

        response = self.client.post(
            reverse("queue-ranked-match"),
            {"deck_id": self.player_deck.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("Unique", response.json()["error"])

    def test_game_create_rejects_deck_when_card_becomes_unique(self):
        self.title.config = {
            "min_cards_in_deck": 1,
            "deck_size_limit": 30,
            "deck_card_max_count": 9,
        }
        self.title.save(update_fields=["config"])
        deck_card = self.player_deck.deckcard_set.first()
        deck_card.count = 2
        deck_card.save(update_fields=["count"])
        CardTrait.objects.create(card=deck_card.card, trait_slug="unique")

        response = self.client.post(
            reverse("game-create"),
            {
                "player_deck_id": self.player_deck.id,
                "ai_deck_id": self.ai_deck.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("Unique", response.json()["error"])

    def test_game_create_allows_ai_deck_outside_player_rule_limits(self):
        self.title.config = {
            "min_cards_in_deck": 6,
            "deck_size_limit": 6,
            "deck_card_max_count": 1,
        }
        self.title.save(update_fields=["config"])

        extra_cards = CardTemplate.objects.filter(
            title=self.title,
            slug__in=["min-card-4", "min-card-5"],
        )
        for card in extra_cards:
            DeckCard.objects.create(deck=self.player_deck, card=card, count=1)

        ai_card = CardTemplate.objects.get(title=self.title, slug="min-card-0")
        CardTrait.objects.create(card=ai_card, trait_slug="unique")
        self.ai_deck.deckcard_set.all().delete()
        DeckCard.objects.create(deck=self.ai_deck, card=ai_card, count=5)

        response = self.client.post(
            reverse("game-create"),
            {
                "player_deck_id": self.player_deck.id,
                "ai_deck_id": self.ai_deck.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)

    def test_game_create_uses_ordered_ai_deck_and_custom_starting_hand(self):
        self.title.config = {
            "min_cards_in_deck": 4,
            "deck_size_limit": 30,
            "deck_card_max_count": 9,
            "hand_start_size": 1,
        }
        self.title.save(update_fields=["config"])
        ordered_cards = [
            CardTemplate.objects.get(title=self.title, slug="min-card-2"),
            CardTemplate.objects.get(title=self.title, slug="min-card-0"),
            CardTemplate.objects.get(title=self.title, slug="min-card-1"),
        ]
        self.ai_deck.script = {
            "strategy": "control",
            "draw_mode": "ordered",
            "starting_hand_size": 2,
            "draw_order": [card.id for card in ordered_cards],
        }
        self.ai_deck.save(update_fields=["script"])
        self.ai_deck.deckcard_set.all().delete()
        for card in ordered_cards:
            DeckCard.objects.update_or_create(
                deck=self.ai_deck,
                card=card,
                defaults={
                    "count": self.ai_deck.script["draw_order"].count(card.id),
                },
            )

        game = GameService.create_game(
            self.player_deck,
            self.ai_deck,
            randomize_starting_player=False,
        )
        GameService.step(game.id)
        game.refresh_from_db()
        state = game.game_state

        def slugs(card_ids):
            return [state.cards[card_id].template_slug for card_id in card_ids]

        self.assertEqual(state.opening_hand_sizes["side_b"], 2)
        self.assertEqual(slugs(state.hands["side_b"]), ["min-card-2", "min-card-0"])
        self.assertEqual(slugs(state.decks["side_b"]), ["min-card-1"])

    def test_queue_status_cancels_entry_when_deck_becomes_invalid(self):
        queue_entry = MatchmakingQueue.objects.create(
            user=self.user,
            deck=self.player_deck,
            elo_rating=1200,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_RAPID,
        )
        self.title.config = {
            "min_cards_in_deck": 1,
            "deck_size_limit": 3,
            "deck_card_max_count": 9,
        }
        self.title.save(update_fields=["config"])

        response = self.client.get(
            reverse("matchmaking-status", kwargs={"title_slug": self.title.slug}),
            {"ladder_type": Game.LADDER_TYPE_RAPID},
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.json()["in_queue"])
        self.assertIn("Removed from queue", response.json()["error"])
        queue_entry.refresh_from_db()
        self.assertEqual(queue_entry.status, MatchmakingQueue.STATUS_CANCELLED)

    def test_queue_status_cancels_entry_when_card_becomes_unique(self):
        queue_entry = MatchmakingQueue.objects.create(
            user=self.user,
            deck=self.player_deck,
            elo_rating=1200,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_RAPID,
        )
        self.title.config = {
            "min_cards_in_deck": 1,
            "deck_size_limit": 30,
            "deck_card_max_count": 9,
        }
        self.title.save(update_fields=["config"])
        deck_card = self.player_deck.deckcard_set.first()
        deck_card.count = 2
        deck_card.save(update_fields=["count"])
        CardTrait.objects.create(card=deck_card.card, trait_slug="unique")

        response = self.client.get(
            reverse("matchmaking-status", kwargs={"title_slug": self.title.slug}),
            {"ladder_type": Game.LADDER_TYPE_RAPID},
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.json()["in_queue"])
        self.assertIn("Unique", response.json()["error"])
        queue_entry.refresh_from_db()
        self.assertEqual(queue_entry.status, MatchmakingQueue.STATUS_CANCELLED)

    def test_queue_request_cancels_existing_entry_when_card_becomes_unique(self):
        queue_entry = MatchmakingQueue.objects.create(
            user=self.user,
            deck=self.player_deck,
            elo_rating=1200,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_RAPID,
        )
        self.title.config = {
            "min_cards_in_deck": 1,
            "deck_size_limit": 30,
            "deck_card_max_count": 9,
        }
        self.title.save(update_fields=["config"])
        deck_card = self.player_deck.deckcard_set.first()
        deck_card.count = 2
        deck_card.save(update_fields=["count"])
        CardTrait.objects.create(card=deck_card.card, trait_slug="unique")

        response = self.client.post(
            reverse("queue-ranked-match"),
            {"deck_id": self.player_deck.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("Unique", response.json()["error"])
        queue_entry.refresh_from_db()
        self.assertEqual(queue_entry.status, MatchmakingQueue.STATUS_CANCELLED)

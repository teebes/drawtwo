from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.authentication.models import Friendship
from apps.builder.models import CardTemplate, CardTrait, HeroTemplate, Title
from apps.collection.models import Deck, DeckCard
from apps.gameplay.models import ELORatingChange, FriendlyChallenge, Game
from apps.gameplay.services import GameService

User = get_user_model()


class FriendlyChallengesAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Users
        self.user_a = User.objects.create_user(email="a@example.com", username="usera")
        self.user_b = User.objects.create_user(email="b@example.com", username="userb")

        # Title and heroes
        self.title = Title.objects.create(
            slug="test-title",
            name="Test Title",
            author=self.user_a,
            config={"min_cards_in_deck": 4},
        )
        self.hero_a = HeroTemplate.objects.create(
            title=self.title, slug="hero-a", name="Hero A", health=10
        )
        self.hero_b = HeroTemplate.objects.create(
            title=self.title, slug="hero-b", name="Hero B", health=10
        )

        # Decks
        self.deck_a = Deck.objects.create(
            title=self.title, user=self.user_a, name="A Deck", hero=self.hero_a
        )
        self.deck_b = Deck.objects.create(
            title=self.title, user=self.user_b, name="B Deck", hero=self.hero_b
        )

        # Add some cards to both decks so the game doesn't instantly end
        for i in range(0, 4):
            card = CardTemplate.objects.create(
                title=self.title,
                slug=f"card-{i}",
                name=f"Card {i}",
                cost=1,
            )
            DeckCard.objects.create(deck=self.deck_a, card=card)
            DeckCard.objects.create(deck=self.deck_b, card=card)

        # Accepted friendship (both directions)
        Friendship.objects.create(
            user=self.user_a,
            friend=self.user_b,
            initiated_by=self.user_a,
            status=Friendship.STATUS_ACCEPTED,
        )
        Friendship.objects.create(
            user=self.user_b,
            friend=self.user_a,
            initiated_by=self.user_a,
            status=Friendship.STATUS_ACCEPTED,
        )

    def _create_extra_user(self, index):
        return User.objects.create_user(
            email=f"extra-{index}@example.com",
            username=f"extra-{index}",
        )

    def _create_deck_for_user(self, user, index):
        deck = Deck.objects.create(
            title=self.title,
            user=user,
            name=f"Extra Deck {index}",
            hero=self.hero_b,
        )
        for card in CardTemplate.objects.filter(title=self.title):
            DeckCard.objects.create(deck=deck, card=card)
        return deck

    def test_create_challenge(self):
        self.client.force_authenticate(self.user_a)
        url = reverse("friendly-challenge-create")
        resp = self.client.post(
            url,
            {
                "title_slug": self.title.slug,
                "challengee_user_id": self.user_b.id,
                "challenger_deck_id": self.deck_a.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["challenger"]["id"], self.user_a.id)
        self.assertEqual(data["challengee"]["id"], self.user_b.id)
        self.assertEqual(data["challenger_deck"]["id"], self.deck_a.id)

    def test_list_pending_incoming_and_outgoing(self):
        # Create a challenge from A -> B
        self.client.force_authenticate(self.user_a)
        create_url = reverse("friendly-challenge-create")
        self.client.post(
            create_url,
            {
                "title_slug": self.title.slug,
                "challengee_user_id": self.user_b.id,
                "challenger_deck_id": self.deck_a.id,
            },
            format="json",
        )

        # Outgoing for A
        pending_url_a = reverse(
            "friendly-challenge-pending", kwargs={"title_slug": self.title.slug}
        )
        resp_a = self.client.get(pending_url_a)
        self.assertEqual(resp_a.status_code, 200)
        self.assertEqual(len(resp_a.json()["outgoing"]), 1)
        self.assertEqual(len(resp_a.json()["incoming"]), 0)

        # Incoming for B
        self.client.force_authenticate(self.user_b)
        pending_url_b = reverse(
            "friendly-challenge-pending", kwargs={"title_slug": self.title.slug}
        )
        resp_b = self.client.get(pending_url_b)
        self.assertEqual(resp_b.status_code, 200)
        self.assertEqual(len(resp_b.json()["incoming"]), 1)
        self.assertEqual(len(resp_b.json()["outgoing"]), 0)

    def test_accept_challenge_creates_unrated_game(self):
        # A creates challenge to B
        self.client.force_authenticate(self.user_a)
        create_url = reverse("friendly-challenge-create")
        create_resp = self.client.post(
            create_url,
            {
                "title_slug": self.title.slug,
                "challengee_user_id": self.user_b.id,
                "challenger_deck_id": self.deck_a.id,
            },
            format="json",
        )
        challenge_id = create_resp.json()["id"]

        # B accepts with their deck
        self.client.force_authenticate(self.user_b)
        accept_url = reverse(
            "friendly-challenge-accept", kwargs={"challenge_id": challenge_id}
        )
        accept_resp = self.client.post(
            accept_url,
            {
                "challengee_deck_id": self.deck_b.id,
            },
            format="json",
        )
        self.assertEqual(accept_resp.status_code, 200, accept_resp.content)
        game_id = accept_resp.json()["game_id"]

        # Game is created and flagged friendly
        game = Game.objects.get(id=game_id)
        self.assertEqual(game.type, Game.GAME_TYPE_FRIENDLY)
        self.assertCountEqual(
            [game.side_a.id, game.side_b.id], [self.deck_a.id, self.deck_b.id]
        )

        # Ensure no ELO change record exists for friendly match
        self.assertFalse(ELORatingChange.objects.filter(game=game).exists())

    def test_accept_rematch_creates_distinct_game_when_swapped_matchup_is_active(self):
        previous_game = GameService.create_game(
            self.deck_a,
            self.deck_b,
            randomize_starting_player=False,
        )
        previous_game.type = Game.GAME_TYPE_FRIENDLY
        previous_game.status = Game.GAME_STATUS_ENDED
        previous_game.winner = self.deck_a
        previous_game.save(update_fields=["type", "status", "winner"])

        active_swapped_game = GameService.create_game(
            self.deck_b,
            self.deck_a,
            randomize_starting_player=False,
        )
        active_swapped_game.type = Game.GAME_TYPE_FRIENDLY
        active_swapped_game.status = Game.GAME_STATUS_IN_PROGRESS
        active_swapped_game.save(update_fields=["type", "status"])

        challenge = FriendlyChallenge.objects.create(
            challenger=self.user_a,
            challengee=self.user_b,
            title=self.title,
            challenger_deck=self.deck_a,
            status=FriendlyChallenge.STATUS_PENDING,
            rematch_of=previous_game,
        )

        self.client.force_authenticate(self.user_b)
        accept_resp = self.client.post(
            reverse("friendly-challenge-accept", kwargs={"challenge_id": challenge.id}),
            {"challengee_deck_id": self.deck_b.id},
            format="json",
        )

        self.assertEqual(accept_resp.status_code, 200, accept_resp.content)
        new_game_id = accept_resp.json()["game_id"]
        self.assertNotEqual(new_game_id, active_swapped_game.id)
        challenge.refresh_from_db()
        self.assertEqual(challenge.game_id, new_game_id)

        new_game = Game.objects.get(id=new_game_id)
        self.assertEqual(new_game.side_a_id, self.deck_b.id)
        self.assertEqual(new_game.side_b_id, self.deck_a.id)
        self.assertEqual(new_game.type, Game.GAME_TYPE_FRIENDLY)

    def test_create_challenge_rejects_undersized_deck(self):
        self.title.config = {"min_cards_in_deck": 10}
        self.title.save(update_fields=["config"])

        self.client.force_authenticate(self.user_a)
        url = reverse("friendly-challenge-create")
        resp = self.client.post(
            url,
            {
                "title_slug": self.title.slug,
                "challengee_user_id": self.user_b.id,
                "challenger_deck_id": self.deck_a.id,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("at least 10 cards", resp.json()["error"])

    def test_accept_cancels_challenge_when_challenger_deck_becomes_invalid(self):
        self.client.force_authenticate(self.user_a)
        create_resp = self.client.post(
            reverse("friendly-challenge-create"),
            {
                "title_slug": self.title.slug,
                "challengee_user_id": self.user_b.id,
                "challenger_deck_id": self.deck_a.id,
            },
            format="json",
        )
        challenge_id = create_resp.json()["id"]

        self.title.config = {
            "min_cards_in_deck": 4,
            "deck_size_limit": 30,
            "deck_card_max_count": 1,
        }
        self.title.save(update_fields=["config"])
        deck_card = self.deck_a.deckcard_set.first()
        deck_card.count = 2
        deck_card.save(update_fields=["count"])

        self.client.force_authenticate(self.user_b)
        accept_resp = self.client.post(
            reverse("friendly-challenge-accept", kwargs={"challenge_id": challenge_id}),
            {"challengee_deck_id": self.deck_b.id},
            format="json",
        )

        self.assertEqual(accept_resp.status_code, 400, accept_resp.content)
        self.assertTrue(accept_resp.json()["challenge_cancelled"])
        challenge = FriendlyChallenge.objects.get(id=challenge_id)
        self.assertEqual(challenge.status, FriendlyChallenge.STATUS_CANCELLED)

    def test_list_pending_cancels_challenge_when_card_becomes_unique(self):
        self.client.force_authenticate(self.user_a)
        create_resp = self.client.post(
            reverse("friendly-challenge-create"),
            {
                "title_slug": self.title.slug,
                "challengee_user_id": self.user_b.id,
                "challenger_deck_id": self.deck_a.id,
            },
            format="json",
        )
        challenge_id = create_resp.json()["id"]

        deck_card = self.deck_a.deckcard_set.first()
        deck_card.count = 2
        deck_card.save(update_fields=["count"])
        CardTrait.objects.create(card=deck_card.card, trait_slug="unique")

        self.client.force_authenticate(self.user_b)
        response = self.client.get(
            reverse(
                "friendly-challenge-pending",
                kwargs={"title_slug": self.title.slug},
            )
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["incoming"], [])
        challenge = FriendlyChallenge.objects.get(id=challenge_id)
        self.assertEqual(challenge.status, FriendlyChallenge.STATUS_CANCELLED)

    def test_create_challenge_rejects_when_challenger_has_five_pending(self):
        for i in range(5):
            FriendlyChallenge.objects.create(
                challenger=self.user_a,
                challengee=self._create_extra_user(i),
                title=self.title,
                challenger_deck=self.deck_a,
                status=FriendlyChallenge.STATUS_PENDING,
            )

        self.client.force_authenticate(self.user_a)
        resp = self.client.post(
            reverse("friendly-challenge-create"),
            {
                "title_slug": self.title.slug,
                "challengee_user_id": self.user_b.id,
                "challenger_deck_id": self.deck_a.id,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("You already have 5 active or pending", resp.json()["error"])

    def test_create_challenge_rejects_when_challengee_has_five_pending(self):
        for i in range(5):
            extra_user = self._create_extra_user(i)
            extra_deck = self._create_deck_for_user(extra_user, i)
            FriendlyChallenge.objects.create(
                challenger=extra_user,
                challengee=self.user_b,
                title=self.title,
                challenger_deck=extra_deck,
                status=FriendlyChallenge.STATUS_PENDING,
            )

        self.client.force_authenticate(self.user_a)
        resp = self.client.post(
            reverse("friendly-challenge-create"),
            {
                "title_slug": self.title.slug,
                "challengee_user_id": self.user_b.id,
                "challenger_deck_id": self.deck_a.id,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("already has 5 active or pending", resp.json()["error"])

    def test_create_challenge_rejects_when_challenger_has_five_active_friendlies(
        self,
    ):
        for i in range(5):
            extra_user = self._create_extra_user(i)
            extra_deck = self._create_deck_for_user(extra_user, i)
            game = GameService.create_game(
                self.deck_a,
                extra_deck,
                randomize_starting_player=False,
            )
            game.type = Game.GAME_TYPE_FRIENDLY
            game.status = Game.GAME_STATUS_IN_PROGRESS
            game.save(update_fields=["type", "status"])

        self.client.force_authenticate(self.user_a)
        resp = self.client.post(
            reverse("friendly-challenge-create"),
            {
                "title_slug": self.title.slug,
                "challengee_user_id": self.user_b.id,
                "challenger_deck_id": self.deck_a.id,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("You already have 5 active or pending", resp.json()["error"])

    def test_challenger_can_cancel_pending_challenge(self):
        self.client.force_authenticate(self.user_a)
        create_resp = self.client.post(
            reverse("friendly-challenge-create"),
            {
                "title_slug": self.title.slug,
                "challengee_user_id": self.user_b.id,
                "challenger_deck_id": self.deck_a.id,
            },
            format="json",
        )
        challenge_id = create_resp.json()["id"]

        cancel_resp = self.client.post(
            reverse("friendly-challenge-cancel", kwargs={"challenge_id": challenge_id})
        )

        self.assertEqual(cancel_resp.status_code, 200, cancel_resp.content)
        self.assertEqual(cancel_resp.json()["message"], "Challenge withdrawn")
        challenge = FriendlyChallenge.objects.get(id=challenge_id)
        self.assertEqual(challenge.status, FriendlyChallenge.STATUS_CANCELLED)

        pending_resp = self.client.get(
            reverse(
                "friendly-challenge-pending", kwargs={"title_slug": self.title.slug}
            )
        )
        self.assertEqual(len(pending_resp.json()["outgoing"]), 0)

    def test_challengee_cannot_cancel_pending_challenge(self):
        challenge = FriendlyChallenge.objects.create(
            challenger=self.user_a,
            challengee=self.user_b,
            title=self.title,
            challenger_deck=self.deck_a,
            status=FriendlyChallenge.STATUS_PENDING,
        )

        self.client.force_authenticate(self.user_b)
        resp = self.client.post(
            reverse("friendly-challenge-cancel", kwargs={"challenge_id": challenge.id})
        )

        self.assertEqual(resp.status_code, 403, resp.content)
        challenge.refresh_from_db()
        self.assertEqual(challenge.status, FriendlyChallenge.STATUS_PENDING)

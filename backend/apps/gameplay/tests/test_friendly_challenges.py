from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient

from apps.authentication.models import Friendship
from apps.builder.models import Title, HeroTemplate, CardTemplate
from apps.collection.models import Deck, DeckCard
from apps.gameplay.models import ELORatingChange, Game


User = get_user_model()


class FriendlyChallengesAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Users
        self.user_a = User.objects.create_user(email="a@example.com", username="usera")
        self.user_b = User.objects.create_user(email="b@example.com", username="userb")

        # Title and heroes
        self.title = Title.objects.create(slug="test-title", name="Test Title", author=self.user_a)
        self.hero_a = HeroTemplate.objects.create(title=self.title, slug="hero-a", name="Hero A", health=10)
        self.hero_b = HeroTemplate.objects.create(title=self.title, slug="hero-b", name="Hero B", health=10)

        # Decks
        self.deck_a = Deck.objects.create(title=self.title, user=self.user_a, name="A Deck", hero=self.hero_a)
        self.deck_b = Deck.objects.create(title=self.title, user=self.user_b, name="B Deck", hero=self.hero_b)

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
        Friendship.objects.create(user=self.user_a, friend=self.user_b, initiated_by=self.user_a, status=Friendship.STATUS_ACCEPTED)
        Friendship.objects.create(user=self.user_b, friend=self.user_a, initiated_by=self.user_a, status=Friendship.STATUS_ACCEPTED)

    def test_create_challenge(self):
        self.client.force_authenticate(self.user_a)
        url = reverse('friendly-challenge-create')
        resp = self.client.post(url, {
            'title_slug': self.title.slug,
            'challengee_user_id': self.user_b.id,
            'challenger_deck_id': self.deck_a.id,
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertEqual(data['status'], 'pending')
        self.assertEqual(data['challenger']['id'], self.user_a.id)
        self.assertEqual(data['challengee']['id'], self.user_b.id)
        self.assertEqual(data['challenger_deck']['id'], self.deck_a.id)

    def test_list_pending_incoming_and_outgoing(self):
        # Create a challenge from A -> B
        self.client.force_authenticate(self.user_a)
        create_url = reverse('friendly-challenge-create')
        self.client.post(create_url, {
            'title_slug': self.title.slug,
            'challengee_user_id': self.user_b.id,
            'challenger_deck_id': self.deck_a.id,
        }, format='json')

        # Outgoing for A
        pending_url_a = reverse('friendly-challenge-pending', kwargs={'title_slug': self.title.slug})
        resp_a = self.client.get(pending_url_a)
        self.assertEqual(resp_a.status_code, 200)
        self.assertEqual(len(resp_a.json()['outgoing']), 1)
        self.assertEqual(len(resp_a.json()['incoming']), 0)

        # Incoming for B
        self.client.force_authenticate(self.user_b)
        pending_url_b = reverse('friendly-challenge-pending', kwargs={'title_slug': self.title.slug})
        resp_b = self.client.get(pending_url_b)
        self.assertEqual(resp_b.status_code, 200)
        self.assertEqual(len(resp_b.json()['incoming']), 1)
        self.assertEqual(len(resp_b.json()['outgoing']), 0)

    def test_accept_challenge_creates_unrated_game(self):
        # A creates challenge to B
        self.client.force_authenticate(self.user_a)
        create_url = reverse('friendly-challenge-create')
        create_resp = self.client.post(create_url, {
            'title_slug': self.title.slug,
            'challengee_user_id': self.user_b.id,
            'challenger_deck_id': self.deck_a.id,
        }, format='json')
        challenge_id = create_resp.json()['id']

        # B accepts with their deck
        self.client.force_authenticate(self.user_b)
        accept_url = reverse('friendly-challenge-accept', kwargs={'challenge_id': challenge_id})
        accept_resp = self.client.post(accept_url, {
            'challengee_deck_id': self.deck_b.id,
        }, format='json')
        self.assertEqual(accept_resp.status_code, 200, accept_resp.content)
        game_id = accept_resp.json()['game_id']

        # Game is created and flagged friendly
        game = Game.objects.get(id=game_id)
        self.assertEqual(game.type, Game.GAME_TYPE_FRIENDLY)
        self.assertCountEqual([game.side_a.id, game.side_b.id], [self.deck_a.id, self.deck_b.id])

        # Ensure no ELO change record exists for friendly match
        self.assertFalse(ELORatingChange.objects.filter(game=game).exists())

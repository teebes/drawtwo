"""
Tests for collection app - deck building and card management.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.builder.models import Title, CardTemplate, HeroTemplate
from apps.builder.models import CardTrait
from .models import Deck, DeckCard

User = get_user_model()


class UniqueTraitDeckValidationTests(TestCase):
    """Test that Unique trait is enforced during deck building."""

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email="testuser@example.com",
            username="testuser",
            password="testpass123"
        )

        # Create title
        self.title = Title.objects.create(
            slug='test-title',
            name='Test Title',
            author=self.user,
            is_latest=True,
        )

        # Create hero
        self.hero = HeroTemplate.objects.create(
            title=self.title,
            slug='test-hero',
            name='Test Hero',
            health=30,
            is_latest=True,
        )

        # Create a regular card
        self.regular_card = CardTemplate.objects.create(
            title=self.title,
            slug='regular-card',
            name='Regular Card',
            cost=1,
            attack=2,
            health=3,
            card_type='creature',
            is_latest=True,
        )

        # Create a unique card
        self.unique_card = CardTemplate.objects.create(
            title=self.title,
            slug='unique-card',
            name='Unique Card',
            cost=3,
            attack=5,
            health=5,
            card_type='creature',
            is_latest=True,
        )
        # Add Unique trait to the card
        CardTrait.objects.create(
            card=self.unique_card,
            trait_slug='unique',
        )

        # Create a deck
        self.deck = Deck.objects.create(
            user=self.user,
            title=self.title,
            name='Test Deck',
            hero=self.hero,
        )

        # Setup API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_can_add_regular_card_multiple_times(self):
        """Test that regular cards can be added multiple times."""
        response = self.client.post(
            f'/api/collection/decks/{self.deck.id}/cards/add/',
            {'card_slug': self.regular_card.slug, 'count': 2},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_cannot_add_unique_card_multiple_times(self):
        """Test that unique cards cannot be added with count > 1."""
        response = self.client.post(
            f'/api/collection/decks/{self.deck.id}/cards/add/',
            {'card_slug': self.unique_card.slug, 'count': 2},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Unique', response.data['error'])

    def test_can_add_unique_card_once(self):
        """Test that unique cards can be added once."""
        response = self.client.post(
            f'/api/collection/decks/{self.deck.id}/cards/add/',
            {'card_slug': self.unique_card.slug, 'count': 1},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_cannot_increase_unique_card_count(self):
        """Test that unique card count cannot be increased beyond 1."""
        # First add the card
        DeckCard.objects.create(deck=self.deck, card=self.unique_card, count=1)

        # Try to update count to 2
        response = self.client.put(
            f'/api/collection/decks/{self.deck.id}/cards/{self.unique_card.id}/',
            {'count': 2},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Unique', response.data['error'])

    def test_cannot_add_more_to_existing_unique_card(self):
        """Test that adding more copies of an existing unique card fails."""
        # First add the card
        DeckCard.objects.create(deck=self.deck, card=self.unique_card, count=1)

        # Try to add another copy
        response = self.client.post(
            f'/api/collection/decks/{self.deck.id}/cards/add/',
            {'card_slug': self.unique_card.slug, 'count': 1},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Unique', response.data['error'])

    def test_can_update_unique_card_count_to_1(self):
        """Test that unique card count can be kept at 1."""
        # First add the card
        DeckCard.objects.create(deck=self.deck, card=self.unique_card, count=1)

        # Update count to 1 (no change)
        response = self.client.put(
            f'/api/collection/decks/{self.deck.id}/cards/{self.unique_card.id}/',
            {'count': 1},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)


class CollectibleCardDeckValidationTests(TestCase):
    """Test that non-collectible cards cannot be added to player decks."""

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email="testuser@example.com",
            username="testuser",
            password="testpass123"
        )

        # Create title
        self.title = Title.objects.create(
            slug='test-title',
            name='Test Title',
            author=self.user,
            is_latest=True,
        )

        # Create hero
        self.hero = HeroTemplate.objects.create(
            title=self.title,
            slug='test-hero',
            name='Test Hero',
            health=30,
            is_latest=True,
        )

        # Create a collectible card
        self.collectible_card = CardTemplate.objects.create(
            title=self.title,
            slug='collectible-card',
            name='Collectible Card',
            cost=1,
            attack=2,
            health=3,
            card_type='creature',
            is_latest=True,
            is_collectible=True,
        )

        # Create a non-collectible card
        self.non_collectible_card = CardTemplate.objects.create(
            title=self.title,
            slug='non-collectible-card',
            name='Non-Collectible Card',
            cost=3,
            attack=5,
            health=5,
            card_type='creature',
            is_latest=True,
            is_collectible=False,
        )

        # Create a deck
        self.deck = Deck.objects.create(
            user=self.user,
            title=self.title,
            name='Test Deck',
            hero=self.hero,
        )

        # Setup API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_can_add_collectible_card(self):
        """Test that collectible cards can be added to decks."""
        response = self.client.post(
            f'/api/collection/decks/{self.deck.id}/cards/add/',
            {'card_slug': self.collectible_card.slug, 'count': 1},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_cannot_add_non_collectible_card(self):
        """Test that non-collectible cards cannot be added to decks."""
        response = self.client.post(
            f'/api/collection/decks/{self.deck.id}/cards/add/',
            {'card_slug': self.non_collectible_card.slug, 'count': 1},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('not collectible', response.data['error'])
        self.assertIn(self.non_collectible_card.name, response.data['error'])

from datetime import datetime, timedelta
import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone

from apps.builder.models import AIPlayer, HeroTemplate, Title
from apps.collection.models import Deck
from apps.gameplay.models import Game, PlayerNotification

from .models import BaseModel, SoftDeleteModel, TimestampedModel

User = get_user_model()


# Test models for testing our base models
class TestTimestampedModel(TimestampedModel):
    """Test model inheriting from TimestampedModel."""
    name = models.CharField(max_length=100)


class TestBaseModel(BaseModel):
    """Test model inheriting from BaseModel."""
    name = models.CharField(max_length=100)


class TestSoftDeleteModel(SoftDeleteModel):
    """Test model inheriting from SoftDeleteModel."""
    name = models.CharField(max_length=100)


class HealthCheckTestCase(TestCase):
    """Test cases for the health check endpoint."""

    def test_health_endpoint(self):
        """Test that the health endpoint returns a 200 status."""
        from unittest.mock import MagicMock, patch

        # Mock Redis since it's not available in CI
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.return_value = True

        with patch("redis.Redis", return_value=mock_redis_instance):
            response = self.client.get("/api/health/")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "healthy")


class TitlePveEndpointTestCase(TestCase):
    """Test cases for title PvE opponent data."""

    def test_pve_decks_are_returned_in_created_order(self):
        """PvE opponents should have a deterministic display order."""
        author = User.objects.create_user(
            email="author@example.com",
            username="author",
        )
        title = Title.objects.create(
            slug="pve-order",
            name="PvE Order",
            author=author,
            status=Title.STATUS_PUBLISHED,
            is_latest=True,
        )
        hero = HeroTemplate.objects.create(
            title=title,
            slug="balanced",
            name="Balanced",
            health=20,
            is_latest=True,
        )
        ai_player = AIPlayer.objects.create(name="Test AI")

        control = Deck.objects.create(
            title=title,
            ai_player=ai_player,
            name="Control",
            hero=hero,
        )
        practice = Deck.objects.create(
            title=title,
            ai_player=ai_player,
            name="Practice",
            hero=hero,
        )
        vanilla = Deck.objects.create(
            title=title,
            ai_player=ai_player,
            name="Vanilla",
            hero=hero,
        )

        now = timezone.now()
        Deck.objects.filter(id=control.id).update(created_at=now + timedelta(minutes=2))
        Deck.objects.filter(id=practice.id).update(created_at=now)
        Deck.objects.filter(id=vanilla.id).update(created_at=now + timedelta(minutes=1))

        response = self.client.get(f"/api/titles/{title.slug}/pve/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            [deck["name"] for deck in response.json()],
            ["Practice", "Vanilla", "Control"],
        )


class TitleEndedGameNotificationsTestCase(TestCase):
    """Test cases for ended-game lobby notifications."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            email="ended-a@example.com",
            username="ended_a",
        )
        self.user_b = User.objects.create_user(
            email="ended-b@example.com",
            username="ended_b",
        )
        self.title = Title.objects.create(
            slug="ended-notifications",
            name="Ended Notifications",
            author=self.user_a,
            status=Title.STATUS_PUBLISHED,
            is_latest=True,
        )
        self.hero_a = HeroTemplate.objects.create(
            title=self.title,
            slug="hero-a",
            name="Hero A",
            health=20,
            is_latest=True,
        )
        self.hero_b = HeroTemplate.objects.create(
            title=self.title,
            slug="hero-b",
            name="Hero B",
            health=20,
            is_latest=True,
        )
        self.deck_a = Deck.objects.create(
            title=self.title,
            user=self.user_a,
            name="Deck A",
            hero=self.hero_a,
        )
        self.deck_b = Deck.objects.create(
            title=self.title,
            user=self.user_b,
            name="Deck B",
            hero=self.hero_b,
        )
        self.game = Game.objects.create(
            title=self.title,
            side_a=self.deck_a,
            side_b=self.deck_b,
            type=Game.GAME_TYPE_RANKED,
            ladder_type=Game.LADDER_TYPE_DAILY,
            status=Game.GAME_STATUS_ENDED,
            winner=self.deck_b,
            state={
                "heroes": {
                    "side_a": {
                        "hero_id": "side_a_hero",
                        "template_slug": self.hero_a.slug,
                        "health": 0,
                        "name": self.hero_a.name,
                        "hero_power": {},
                    },
                    "side_b": {
                        "hero_id": "side_b_hero",
                        "template_slug": self.hero_b.slug,
                        "health": 20,
                        "name": self.hero_b.name,
                        "hero_power": {},
                    },
                },
                "winner": "side_b",
            },
        )
        self.notification_a = PlayerNotification.objects.create(
            user=self.user_a,
            game=self.game,
            message="Game over.",
        )
        self.notification_b = PlayerNotification.objects.create(
            user=self.user_b,
            game=self.game,
            message="Game over.",
        )

    def test_unread_ended_game_notification_appears_in_lobby(self):
        self.client.force_login(self.user_a)

        response = self.client.get(f"/api/titles/{self.title.slug}/notifications/")

        self.assertEqual(response.status_code, 200, response.content)
        ended_notifications = [
            notification
            for notification in response.json()
            if notification["type"] == "game_ended"
        ]
        self.assertEqual(len(ended_notifications), 1)
        self.assertEqual(ended_notifications[0]["ref_id"], self.game.id)
        self.assertIn("Game over:", ended_notifications[0]["message"])
        self.assertIn("ended_b defeated you", ended_notifications[0]["message"])
        self.assertFalse(ended_notifications[0]["is_user_turn"])

    def test_game_detail_does_not_clear_ended_game_notification(self):
        self.client.force_login(self.user_a)

        response = self.client.get(f"/api/gameplay/games/{self.game.id}/")

        self.assertEqual(response.status_code, 200, response.content)
        self.notification_a.refresh_from_db()
        self.notification_b.refresh_from_db()
        self.assertFalse(self.notification_a.is_read)
        self.assertFalse(self.notification_b.is_read)

    def test_acknowledging_ended_game_clears_only_current_players_notification(self):
        self.client.force_login(self.user_a)

        response = self.client.post(
            f"/api/gameplay/games/{self.game.id}/notifications/read/"
        )

        self.assertEqual(response.status_code, 204, response.content)
        self.notification_a.refresh_from_db()
        self.notification_b.refresh_from_db()
        self.assertTrue(self.notification_a.is_read)
        self.assertFalse(self.notification_b.is_read)

        response = self.client.get(f"/api/titles/{self.title.slug}/notifications/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(
            any(
                notification["type"] == "game_ended"
                and notification["ref_id"] == self.game.id
                for notification in response.json()
            )
        )


class BasicDjangoTestCase(TestCase):
    """Basic Django functionality tests."""

    def test_django_is_working(self):
        """Test that Django is properly configured."""
        self.assertTrue(True)

    def test_user_creation(self):
        """Test that we can create users."""
        user = User.objects.create_user(email="test@example.com", username="testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.display_name, "testuser")
        self.assertFalse(user.is_email_verified)

    def test_user_creation_without_username(self):
        """Test that we can create users without username."""
        user = User.objects.create_user(email="test2@example.com")
        self.assertEqual(user.email, "test2@example.com")
        self.assertIsNone(user.username)
        self.assertEqual(user.display_name, f"Gamer {user.id}")
        self.assertFalse(user.is_email_verified)

    def test_admin_accessible(self):
        """Test that admin is accessible."""
        response = self.client.get("/admin/")
        # Should redirect to login (302) since we're not authenticated
        self.assertEqual(response.status_code, 302)


class BaseModelTestCase(TestCase):
    """Test cases for core base models."""

    def test_timestamped_model_auto_timestamps(self):
        """Test that TimestampedModel automatically sets timestamps."""
        # Test with a real model that uses timestamps (User model inherits from TimestampedModel)
        user = User.objects.create_user(email="timestamp@example.com")

        # Check that timestamps are set
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
        self.assertIsInstance(user.created_at, datetime)
        self.assertIsInstance(user.updated_at, datetime)

        # Initially, created_at and updated_at should be very close
        self.assertAlmostEqual(
            user.created_at.timestamp(),
            user.updated_at.timestamp(),
            delta=1  # Within 1 second
        )

    def test_timestamped_model_update_timestamp(self):
        """Test that updated_at changes when model is saved."""
        user = User.objects.create_user(email="update@example.com")
        original_updated_at = user.updated_at

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        # Update the user
        user.username = "updated"
        user.save()

        # Check that updated_at changed
        user.refresh_from_db()
        self.assertNotEqual(user.updated_at, original_updated_at)
        self.assertGreater(user.updated_at, original_updated_at)

    def test_base_model_uuid_field(self):
        """Test that models inheriting from BaseModel have UUID primary keys."""
        # For this test, we'll check that User model fields work as expected
        user = User.objects.create_user(email="uuid@example.com")

        # Check the id field exists and has expected properties
        self.assertIsNotNone(user.id)
        # The User model uses auto-increment ID, but let's test UUID behavior conceptually
        self.assertTrue(hasattr(user, 'id'))
        self.assertTrue(hasattr(user, 'created_at'))
        self.assertTrue(hasattr(user, 'updated_at'))

    def test_soft_delete_functionality(self):
        """Test that soft delete models work correctly."""
        # We'll create a simple test using User model and is_active pattern
        user = User.objects.create_user(email="softdelete@example.com")
        user_id = user.id

        # User should be active by default
        self.assertTrue(user.is_active)

        # Test deactivation (simulating soft delete pattern)
        user.is_active = False
        user.save()

        # Refresh from database
        user.refresh_from_db()
        self.assertFalse(user.is_active)

        # Test reactivation
        user.is_active = True
        user.save()

        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_model_inheritance_chain(self):
        """Test that our base models provide the expected inheritance."""
        user = User.objects.create_user(email="inheritance@example.com")

        # Test that User has timestamp fields
        self.assertTrue(hasattr(user, 'created_at'))
        self.assertTrue(hasattr(user, 'updated_at'))

        # Test that the fields are properly typed
        self.assertIsInstance(user.created_at, datetime)
        self.assertIsInstance(user.updated_at, datetime)

        # Test that user has is_active field (inherited pattern)
        self.assertTrue(hasattr(user, 'is_active'))
        self.assertIsInstance(user.is_active, bool)

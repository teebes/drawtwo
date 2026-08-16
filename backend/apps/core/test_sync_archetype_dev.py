from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.builder.models import CardTemplate, HeroTemplate, Title
from apps.collection.models import Deck, DeckCard, StarterDeckProvisioning
from apps.collection.tasks import provision_starter_decks_for_user_task

User = get_user_model()


@override_settings(DEBUG=True)
class SyncArchetypeDevCommandTests(TestCase):
    def sync(self):
        output = StringIO()
        call_command("sync_archetype_dev", stdout=output)
        return output.getvalue()

    def test_fresh_sync_imports_canonical_content_and_enables_starter_deck(self):
        with patch("apps.collection.signals.provision_starter_decks_for_user"):
            output = self.sync()

        title = Title.objects.get(slug="archetype", is_latest=True)
        self.assertEqual(title.status, Title.STATUS_PUBLISHED)
        self.assertEqual(title.config["deck_size_limit"], 40)
        self.assertEqual(title.config["deck_card_max_count"], 4)
        self.assertEqual(
            CardTemplate.objects.filter(title=title, is_latest=True).count(),
            36,
        )
        self.assertEqual(
            HeroTemplate.objects.filter(title=title, is_latest=True).count(),
            5,
        )
        self.assertTrue(
            CardTemplate.objects.filter(
                title=title,
                slug="dragoon",
                is_latest=True,
            ).exists()
        )
        self.assertTrue(
            HeroTemplate.objects.filter(
                title=title,
                slug="sniper",
                is_latest=True,
            ).exists()
        )
        self.assertIn("43 resources", output)

        user = User.objects.create_user(email="fresh-starter@example.com")
        deck = Deck.objects.get(user=user, title=title, name="Your First Deck")
        self.assertEqual(deck.hero.slug, "sniper")
        self.assertEqual(deck.deck_size, 40)
        self.assertEqual(deck.deckcard_set.count(), 23)

    def test_existing_sync_only_adds_missing_starter_resources(self):
        with patch("apps.collection.signals.provision_starter_decks_for_user"):
            author = User.objects.create_user(email="local-author@example.com")
            player = User.objects.create_user(email="local-player@example.com")

        local_config = {
            "deck_size_limit": 77,
            "min_cards_in_deck": 2,
            "deck_card_max_count": 11,
            "custom_local_rule": True,
        }
        title = Title.objects.create(
            slug="archetype",
            name="Locally Edited Archetype",
            description="Keep this local description.",
            author=author,
            status=Title.STATUS_DRAFT,
            config=local_config,
        )
        local_hero = HeroTemplate.objects.create(
            title=title,
            slug="local-hero",
            name="Local Hero",
            health=17,
        )
        edited_zap = CardTemplate.objects.create(
            title=title,
            slug="zap",
            name="Locally Edited Zap",
            card_type=CardTemplate.CARD_TYPE_SPELL,
            description="Keep this local card edit.",
            cost=9,
        )
        local_card = CardTemplate.objects.create(
            title=title,
            slug="local-card",
            name="Local Card",
            card_type=CardTemplate.CARD_TYPE_CREATURE,
            cost=1,
            attack=1,
            health=1,
        )
        local_deck = Deck.objects.create(
            user=player,
            title=title,
            name="Local Work",
            hero=local_hero,
        )
        DeckCard.objects.create(deck=local_deck, card=local_card, count=1)

        first_output = self.sync()
        second_output = self.sync()

        title.refresh_from_db()
        edited_zap.refresh_from_db()
        local_deck.refresh_from_db()
        self.assertEqual(title.name, "Locally Edited Archetype")
        self.assertEqual(title.description, "Keep this local description.")
        self.assertEqual(title.status, Title.STATUS_DRAFT)
        self.assertEqual(title.config, local_config)
        self.assertEqual(edited_zap.name, "Locally Edited Zap")
        self.assertEqual(edited_zap.description, "Keep this local card edit.")
        self.assertEqual(edited_zap.cost, 9)
        self.assertEqual(local_deck.name, "Local Work")
        self.assertTrue(
            CardTemplate.objects.filter(pk=local_card.pk, is_latest=True).exists()
        )
        self.assertTrue(
            HeroTemplate.objects.filter(pk=local_hero.pk, is_latest=True).exists()
        )
        self.assertEqual(
            CardTemplate.objects.filter(
                title=title,
                slug="dragoon",
                is_latest=True,
            ).count(),
            1,
        )
        self.assertFalse(
            CardTemplate.objects.filter(
                title=title,
                slug="destiny",
                is_latest=True,
            ).exists()
        )
        self.assertIn("23 resources", first_output)
        self.assertIn("0 resources", second_output)

    def test_pending_user_recovers_after_sync_restores_dragoon(self):
        with patch("apps.collection.signals.provision_starter_decks_for_user"):
            self.sync()

        title = Title.objects.get(slug="archetype", is_latest=True)
        CardTemplate.objects.get(
            title=title,
            slug="dragoon",
            is_latest=True,
        ).delete()

        with self.assertLogs("apps.collection.provisioning", level="ERROR"):
            user = User.objects.create_user(email="pending-starter@example.com")
        provisioning = StarterDeckProvisioning.objects.get(
            user=user,
            title_slug="archetype",
        )
        self.assertIsNone(provisioning.completed_at)
        self.assertIn("dragoon", provisioning.last_error)

        output = self.sync()
        self.assertIn("1 resources", output)
        provisioning.last_attempted_at = timezone.now() - timedelta(minutes=1)
        provisioning.save(update_fields=["last_attempted_at", "updated_at"])

        self.assertEqual(provision_starter_decks_for_user_task.run(user.pk), 1)
        provisioning.refresh_from_db()
        self.assertIsNotNone(provisioning.completed_at)
        self.assertEqual(provisioning.last_error, "")
        self.assertEqual(provisioning.deck.deck_size, 40)

    @override_settings(DEBUG=False)
    def test_sync_is_refused_outside_debug(self):
        with self.assertRaisesMessage(
            CommandError,
            "This command can only be run when DEBUG is enabled.",
        ):
            self.sync()


@override_settings(DEBUG=True)
class SeedArchetypeDevCommandTests(TestCase):
    def test_seed_uses_tracked_canonical_snapshot(self):
        with patch("apps.collection.signals.provision_starter_decks_for_user"):
            call_command("seed_archetype_dev", stdout=StringIO())

        title = Title.objects.get(slug="archetype", is_latest=True)
        self.assertEqual(title.config["deck_size_limit"], 40)
        self.assertEqual(title.config["deck_card_max_count"], 4)
        self.assertEqual(
            set(
                HeroTemplate.objects.filter(
                    title=title,
                    is_latest=True,
                ).values_list("slug", flat=True)
            ),
            {"berserker", "bloodmage", "commander", "healer", "sniper"},
        )
        self.assertTrue(
            CardTemplate.objects.filter(
                title=title,
                slug="dragoon",
                is_latest=True,
            ).exists()
        )

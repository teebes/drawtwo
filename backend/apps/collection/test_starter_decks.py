import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import DatabaseError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.builder.models import CardTemplate, CardTrait, HeroTemplate, Title
from apps.collection.compositions import parse_composition_code
from apps.collection.models import (
    Deck,
    StarterDeckProgram,
    StarterDeckProvisioning,
    UserTitleDeckPreference,
)
from apps.collection.provisioning import (
    StarterDeckDefinition,
    StarterDeckProvisioningError,
    load_starter_deck_definitions,
    provision_starter_deck_for_user,
    provision_starter_decks_for_user,
    retry_pending_starter_decks_for_user,
)
from apps.collection.tasks import (
    provision_starter_decks_for_user_task,
    reconcile_starter_deck_provisionings,
)
from apps.collection.validation import validate_deck_for_play

User = get_user_model()


class ArchetypeStarterDeckManifestTests(SimpleTestCase):
    def test_manifest_captures_production_deck_four_by_stable_slugs(self):
        definitions = load_starter_deck_definitions()
        archetype = next(
            definition
            for definition in definitions
            if definition.title_slug == "archetype"
        )

        self.assertEqual(archetype.name, "Your First Deck")
        self.assertEqual(archetype.description, "")
        self.assertEqual(archetype.hero_slug, "sniper")

        card_counts = parse_composition_code(archetype.composition_code)
        self.assertEqual(len(card_counts), 23)
        self.assertEqual(sum(card_counts.values()), 40)
        self.assertEqual(card_counts["dragoon"], 2)
        self.assertEqual(card_counts["shieldwall"], 3)

    def test_loader_rejects_a_missing_manifest_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            load_starter_deck_definitions.cache_clear()
            with (
                patch(
                    "apps.collection.provisioning.STARTER_DECK_MANIFEST_DIR",
                    Path(directory),
                ),
                self.assertRaises(StarterDeckProvisioningError),
            ):
                load_starter_deck_definitions()
        load_starter_deck_definitions.cache_clear()


class ArchetypeStarterDeckIntegrationTests(TestCase):
    expected_card_counts = {
        "abomination": 1,
        "ambusher": 2,
        "brute": 2,
        "cheerleader": 1,
        "cleave": 2,
        "decoy": 3,
        "dragoon": 2,
        "drawtwo": 2,
        "grenade": 2,
        "herald": 3,
        "hornet": 1,
        "knight": 2,
        "medic": 1,
        "meteor": 2,
        "opportunist": 1,
        "phalanx": 1,
        "phoenix": 1,
        "remove": 2,
        "sharpen": 1,
        "shieldwall": 3,
        "silence": 1,
        "soldier": 2,
        "zap": 2,
    }
    unique_slugs = {
        "abomination",
        "cheerleader",
        "hornet",
        "opportunist",
        "phalanx",
        "phoenix",
    }

    def setUp(self):
        self.author = User.objects.create_user(email="archetype-author@example.com")
        self.title = Title.objects.create(
            slug="archetype",
            name="Archetype",
            author=self.author,
            status=Title.STATUS_PUBLISHED,
            config={
                "deck_size_limit": 40,
                "min_cards_in_deck": 10,
                "deck_card_max_count": 4,
            },
        )
        self.hero = HeroTemplate.objects.create(
            title=self.title,
            slug="sniper",
            name="Sniper",
            health=30,
        )
        for slug in self.expected_card_counts:
            card = CardTemplate.objects.create(
                title=self.title,
                slug=slug,
                name=slug.replace("-", " ").title(),
                cost=1,
                attack=1,
                health=1,
            )
            if slug in self.unique_slugs:
                CardTrait.objects.create(card=card, trait_slug="unique")

    def test_real_manifest_provisions_a_complete_legal_archetype_deck(self):
        user = User.objects.create_user(email="archetype-new-player@example.com")

        deck = Deck.objects.get(user=user, title=self.title)
        self.assertEqual(deck.name, "Your First Deck")
        self.assertEqual(deck.description, "")
        self.assertEqual(deck.hero, self.hero)
        self.assertEqual(
            dict(deck.deckcard_set.values_list("card__slug", "count")),
            self.expected_card_counts,
        )
        self.assertEqual(deck.deck_size, 40)
        self.assertEqual(validate_deck_for_play(deck), None)
        provisioning = StarterDeckProvisioning.objects.get(
            user=user,
            title_slug=self.title.slug,
        )
        self.assertIsNotNone(provisioning.completed_at)


class StarterDeckProvisioningTests(TestCase):
    def setUp(self):
        cache.clear()
        self.author = User.objects.create_user(email="author@example.com")
        self.title = Title.objects.create(
            slug="starter-test",
            name="Starter Test",
            author=self.author,
            status=Title.STATUS_PUBLISHED,
            config={
                "deck_size_limit": 3,
                "min_cards_in_deck": 3,
                "deck_card_max_count": 2,
            },
        )
        self.hero = HeroTemplate.objects.create(
            title=self.title,
            slug="starter-hero",
            name="Starter Hero",
            health=30,
        )
        self.alpha = CardTemplate.objects.create(
            title=self.title,
            slug="alpha",
            name="Alpha",
            cost=1,
            attack=1,
            health=1,
        )
        self.beta = CardTemplate.objects.create(
            title=self.title,
            slug="beta",
            name="Beta",
            cost=2,
            attack=2,
            health=2,
        )
        self.definition = StarterDeckDefinition(
            title_slug=self.title.slug,
            name="Your First Deck",
            description="Ready to play.",
            hero_slug=self.hero.slug,
            composition_code="dt1.alpha~2.beta~1",
        )
        self.program = StarterDeckProgram.objects.create(
            title_slug=self.title.slug,
            eligible_after=timezone.now(),
        )

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def _create_user(self, email="new-player@example.com"):
        with patch(
            "apps.collection.provisioning.load_starter_deck_definitions",
            return_value=(self.definition,),
        ):
            return User.objects.create_user(email=email)

    def test_new_user_gets_independent_valid_starter_deck(self):
        user = self._create_user()

        deck = Deck.objects.get(user=user, title=self.title)
        self.assertEqual(deck.name, "Your First Deck")
        self.assertEqual(deck.description, "Ready to play.")
        self.assertEqual(deck.hero, self.hero)
        self.assertEqual(
            dict(deck.deckcard_set.values_list("card__slug", "count")),
            {"alpha": 2, "beta": 1},
        )
        self.assertEqual(validate_deck_for_play(deck), None)

        deck.refresh_from_db()
        self.assertIsNotNone(deck.current_revision)
        self.assertEqual(deck.current_revision.deck, deck)
        self.assertEqual(deck.current_revision.source, "create")
        self.assertEqual(
            deck.current_revision.composition.code, self.definition.composition_code
        )

        preference = UserTitleDeckPreference.objects.get(user=user, title=self.title)
        self.assertEqual(preference.last_used_deck, deck)
        provisioning = StarterDeckProvisioning.objects.get(
            user=user,
            title_slug=self.title.slug,
        )
        self.assertIsNotNone(provisioning.completed_at)
        self.assertEqual(provisioning.last_error, "")
        self.assertEqual(provisioning.deck, deck)

    def test_provisioning_is_created_only_and_idempotent(self):
        user = self._create_user()

        user.username = "new-player"
        user.save(update_fields=["username"])
        with patch(
            "apps.collection.provisioning.load_starter_deck_definitions",
            return_value=(self.definition,),
        ):
            provisioned = provision_starter_decks_for_user(user)

        self.assertEqual(provisioned, [])
        self.assertEqual(
            Deck.objects.filter(user=user, title=self.title).count(),
            1,
        )
        deck = Deck.objects.get(user=user, title=self.title)
        self.assertEqual(deck.revisions.count(), 1)

    def test_invalid_starter_content_does_not_block_account_creation(self):
        invalid_definition = StarterDeckDefinition(
            title_slug=self.title.slug,
            name="Your First Deck",
            description="",
            hero_slug=self.hero.slug,
            composition_code="dt1.unknown-card~3",
        )
        with (
            patch(
                "apps.collection.provisioning.load_starter_deck_definitions",
                return_value=(invalid_definition,),
            ),
            self.assertLogs("apps.collection.provisioning", level="ERROR"),
        ):
            user = User.objects.create_user(email="safe-signup@example.com")

        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        self.assertFalse(Deck.objects.filter(user=user).exists())
        provisioning = StarterDeckProvisioning.objects.get(
            user=user,
            title_slug=self.title.slug,
        )
        self.assertIsNone(provisioning.completed_at)
        self.assertIn("unknown-card", provisioning.last_error)

    def test_retired_card_is_rejected_for_a_new_starter_deck(self):
        self.beta.is_latest = False
        self.beta.save(update_fields=["is_latest"])

        with (
            patch(
                "apps.collection.provisioning.load_starter_deck_definitions",
                return_value=(self.definition,),
            ),
            self.assertLogs("apps.collection.provisioning", level="ERROR"),
        ):
            user = User.objects.create_user(email="retired-card@example.com")

        self.assertFalse(Deck.objects.filter(user=user).exists())
        provisioning = StarterDeckProvisioning.objects.get(
            user=user,
            title_slug=self.title.slug,
        )
        self.assertIsNone(provisioning.completed_at)
        self.assertIn("retired card(s): beta", provisioning.last_error)

    def test_pending_new_user_grant_retries_in_background(self):
        late_definition = StarterDeckDefinition(
            title_slug="late-title",
            name="Late Starter",
            description="",
            hero_slug="late-hero",
            composition_code="dt1.late-card~1",
        )
        StarterDeckProgram.objects.create(
            title_slug=late_definition.title_slug,
            eligible_after=timezone.now(),
        )
        with (
            patch(
                "apps.collection.signals."
                "provision_starter_decks_for_user_task.apply_async"
            ) as enqueue,
            self.captureOnCommitCallbacks(execute=True),
            patch(
                "apps.collection.provisioning.load_starter_deck_definitions",
                return_value=(late_definition,),
            ),
        ):
            user = User.objects.create_user(email="late-content@example.com")

        enqueue.assert_called_once_with(args=[user.pk], countdown=30)

        provisioning = StarterDeckProvisioning.objects.get(
            user=user,
            title_slug=late_definition.title_slug,
        )
        self.assertIsNone(provisioning.completed_at)
        self.assertFalse(Deck.objects.filter(user=user).exists())

        late_title = Title.objects.create(
            slug=late_definition.title_slug,
            name="Late Title",
            author=self.author,
            status=Title.STATUS_PUBLISHED,
            config={
                "deck_size_limit": 1,
                "min_cards_in_deck": 1,
                "deck_card_max_count": 1,
            },
        )
        HeroTemplate.objects.create(
            title=late_title,
            slug=late_definition.hero_slug,
            name="Late Hero",
            health=30,
        )
        CardTemplate.objects.create(
            title=late_title,
            slug="late-card",
            name="Late Card",
            cost=1,
            attack=1,
            health=1,
        )

        provisioning.last_attempted_at = timezone.now() - timedelta(minutes=1)
        provisioning.save(update_fields=["last_attempted_at", "updated_at"])
        with patch(
            "apps.collection.provisioning.load_starter_deck_definitions",
            return_value=(late_definition,),
        ):
            provisioned_count = provision_starter_decks_for_user_task.run(user.pk)

        self.assertEqual(provisioned_count, 1)

        client = APIClient()
        client.force_authenticate(user)
        response = client.get(
            reverse(
                "deck-list-by-title",
                kwargs={"title_slug": late_title.slug},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["decks"][0]["name"], "Late Starter")
        provisioning.refresh_from_db()
        self.assertIsNotNone(provisioning.completed_at)

    def test_completed_grant_is_not_recreated_after_user_archives_it(self):
        user = self._create_user(email="archive-starter@example.com")
        deck = Deck.objects.get(user=user, title=self.title)
        deck.archive()

        client = APIClient()
        client.force_authenticate(user)
        response = client.get(
            reverse(
                "deck-list-by-title",
                kwargs={"title_slug": self.title.slug},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(Deck.objects.filter(user=user, title=self.title).count(), 1)

    def test_pre_rollout_existing_user_never_becomes_eligible(self):
        with patch(
            "apps.collection.provisioning.load_starter_deck_definitions",
            return_value=(),
        ):
            user = User.objects.create_user(email="existing-user@example.com")
        User.objects.filter(pk=user.pk).update(
            created_at=self.program.eligible_after - timedelta(days=1)
        )
        user.refresh_from_db()

        with patch(
            "apps.collection.provisioning.load_starter_deck_definitions",
            return_value=(self.definition,),
        ):
            provisioned_count = provision_starter_decks_for_user_task.run(user.pk)
        self.assertEqual(provisioned_count, 0)

        with (
            patch(
                "apps.collection.tasks.load_starter_deck_definitions",
                return_value=(self.definition,),
            ),
            patch(
                "apps.collection.tasks.provision_starter_decks_for_user_task.delay"
            ) as enqueue,
        ):
            dispatched = reconcile_starter_deck_provisionings.run()

        self.assertEqual(dispatched, 0)
        enqueue.assert_not_called()

        client = APIClient()
        client.force_authenticate(user)
        response = client.get(
            reverse(
                "deck-list-by-title",
                kwargs={"title_slug": self.title.slug},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertFalse(Deck.objects.filter(user=user).exists())
        self.assertFalse(
            StarterDeckProvisioning.objects.filter(
                user=user,
                title_slug=self.title.slug,
            ).exists()
        )

    def test_missing_promise_is_recovered_by_background_task(self):
        with (
            patch(
                "apps.collection.signals."
                "provision_starter_decks_for_user_task.apply_async"
            ) as enqueue,
            self.captureOnCommitCallbacks(execute=True),
            patch(
                "apps.collection.provisioning.load_starter_deck_definitions",
                return_value=(self.definition,),
            ),
            patch(
                "apps.collection.provisioning."
                "StarterDeckProvisioning.objects.get_or_create",
                side_effect=DatabaseError("temporary marker write failure"),
            ),
            self.assertLogs("apps.collection.signals", level="ERROR"),
        ):
            with transaction.atomic():
                user = User.objects.create_user(email="missing-promise@example.com")
                self.assertTrue(User.objects.filter(pk=user.pk).exists())

        enqueue.assert_called_once_with(args=[user.pk], countdown=30)

        self.assertFalse(
            StarterDeckProvisioning.objects.filter(
                user=user,
                title_slug=self.title.slug,
            ).exists()
        )

        with patch(
            "apps.collection.provisioning.load_starter_deck_definitions",
            return_value=(self.definition,),
        ):
            provisioned_count = provision_starter_decks_for_user_task.run(user.pk)

        self.assertEqual(provisioned_count, 1)
        provisioning = StarterDeckProvisioning.objects.get(
            user=user,
            title_slug=self.title.slug,
        )
        self.assertIsNotNone(provisioning.completed_at)
        self.assertIsNotNone(provisioning.deck_id)

    def test_deck_list_does_not_create_missing_provisioning_state(self):
        with patch(
            "apps.collection.provisioning.load_starter_deck_definitions",
            return_value=(),
        ):
            user = User.objects.create_user(email="read-only-list@example.com")

        client = APIClient()
        client.force_authenticate(user)
        response = client.get(
            reverse(
                "deck-list-by-title",
                kwargs={"title_slug": self.title.slug},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertFalse(Deck.objects.filter(user=user).exists())
        self.assertFalse(StarterDeckProvisioning.objects.filter(user=user).exists())

    def test_reconciler_repairs_missing_promise_and_dispatches_retry(self):
        with patch(
            "apps.collection.provisioning.load_starter_deck_definitions",
            return_value=(),
        ):
            user = User.objects.create_user(email="reconciled-player@example.com")

        self.assertFalse(
            StarterDeckProvisioning.objects.filter(
                user=user,
                title_slug=self.title.slug,
            ).exists()
        )

        with (
            patch(
                "apps.collection.tasks.load_starter_deck_definitions",
                return_value=(self.definition,),
            ),
            patch(
                "apps.collection.tasks.provision_starter_decks_for_user_task.delay"
            ) as enqueue,
        ):
            dispatched = reconcile_starter_deck_provisionings.run()
            duplicate_dispatches = reconcile_starter_deck_provisionings.run()

        self.assertEqual(dispatched, 1)
        self.assertEqual(duplicate_dispatches, 0)
        provisioning = StarterDeckProvisioning.objects.get(
            user=user,
            title_slug=self.title.slug,
        )
        self.assertIsNone(provisioning.completed_at)
        self.assertIsNotNone(provisioning.last_dispatched_at)
        enqueue.assert_called_once_with(user.pk)

    def test_locked_provisioning_skips_an_account_deleted_after_queueing(self):
        invalid_definition = StarterDeckDefinition(
            title_slug=self.title.slug,
            name=self.definition.name,
            description="",
            hero_slug=self.hero.slug,
            composition_code="dt1.unknown-card~3",
        )
        with (
            patch(
                "apps.collection.provisioning.load_starter_deck_definitions",
                return_value=(invalid_definition,),
            ),
            self.assertLogs("apps.collection.provisioning", level="ERROR"),
        ):
            user = User.objects.create_user(email="deleted-before-retry@example.com")

        queued_user = User.objects.get(pk=user.pk)
        user.anonymize_for_deletion()
        provisioning = StarterDeckProvisioning.objects.get(
            user=user,
            title_slug=self.title.slug,
        )
        deck, created = provision_starter_deck_for_user(
            queued_user,
            self.definition,
            provisioning,
        )

        self.assertIsNone(deck)
        self.assertFalse(created)
        self.assertFalse(Deck.objects.filter(user_id=user.pk).exists())
        provisioning.refresh_from_db()
        self.assertIsNotNone(provisioning.completed_at)
        self.assertEqual(
            provisioning.last_error,
            "Account deleted before provisioning",
        )

    def test_same_name_user_deck_does_not_complete_pending_grant(self):
        invalid_definition = StarterDeckDefinition(
            title_slug=self.title.slug,
            name=self.definition.name,
            description="",
            hero_slug=self.hero.slug,
            composition_code="dt1.unknown-card~3",
        )
        with (
            patch(
                "apps.collection.provisioning.load_starter_deck_definitions",
                return_value=(invalid_definition,),
            ),
            self.assertLogs("apps.collection.provisioning", level="ERROR"),
        ):
            user = User.objects.create_user(email="name-collision@example.com")

        user_deck = Deck.objects.create(
            user=user,
            title=self.title,
            name=self.definition.name,
            description="Player-created deck.",
            hero=self.hero,
        )
        provisioning = StarterDeckProvisioning.objects.get(
            user=user,
            title_slug=self.title.slug,
        )
        provisioning.last_attempted_at = timezone.now() - timedelta(minutes=1)
        provisioning.save(update_fields=["last_attempted_at", "updated_at"])
        with (
            patch(
                "apps.collection.provisioning.load_starter_deck_definitions",
                return_value=(self.definition,),
            ),
            self.assertLogs("apps.collection.provisioning", level="ERROR"),
        ):
            provisioned = retry_pending_starter_decks_for_user(
                user,
                definitions=(self.definition,),
                respect_backoff=True,
            )

        self.assertEqual(provisioned, [])
        self.assertEqual(Deck.objects.filter(user=user).get(), user_deck)
        provisioning.refresh_from_db()
        self.assertIsNone(provisioning.completed_at)
        self.assertIsNone(provisioning.deck_id)
        self.assertIn("already has an active deck", provisioning.last_error)

    def test_failed_grant_retries_are_rate_limited(self):
        invalid_definition = StarterDeckDefinition(
            title_slug=self.title.slug,
            name=self.definition.name,
            description="",
            hero_slug=self.hero.slug,
            composition_code="dt1.unknown-card~3",
        )
        with (
            patch(
                "apps.collection.provisioning.load_starter_deck_definitions",
                return_value=(invalid_definition,),
            ),
            self.assertLogs("apps.collection.provisioning", level="ERROR"),
        ):
            user = User.objects.create_user(email="retry-backoff@example.com")

        immediate = retry_pending_starter_decks_for_user(
            user,
            definitions=(self.definition,),
            respect_backoff=True,
        )
        self.assertEqual(immediate, [])
        self.assertFalse(Deck.objects.filter(user=user).exists())

        provisioning = StarterDeckProvisioning.objects.get(
            user=user,
            title_slug=self.title.slug,
        )
        provisioning.last_attempted_at = timezone.now() - timedelta(minutes=1)
        provisioning.save(update_fields=["last_attempted_at", "updated_at"])
        retried = retry_pending_starter_decks_for_user(
            user,
            definitions=(self.definition,),
            respect_backoff=True,
        )

        self.assertEqual(len(retried), 1)
        self.assertEqual(retried[0].user, user)
        provisioning.refresh_from_db()
        self.assertIsNotNone(provisioning.completed_at)

    def test_registration_api_returns_user_with_listable_starter_deck(self):
        client = APIClient()
        with patch(
            "apps.collection.provisioning.load_starter_deck_definitions",
            return_value=(self.definition,),
        ):
            response = client.post(
                reverse("authentication:register"),
                {"email": "registered-player@example.com"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="registered-player@example.com")
        client.force_authenticate(user)
        deck_response = client.get(
            reverse(
                "deck-list-by-title",
                kwargs={"title_slug": self.title.slug},
            )
        )

        self.assertEqual(deck_response.status_code, status.HTTP_200_OK)
        self.assertEqual(deck_response.data["count"], 1)
        self.assertEqual(deck_response.data["decks"][0]["name"], "Your First Deck")
        self.assertEqual(deck_response.data["decks"][0]["card_count"], 3)
        self.assertEqual(
            deck_response.data["decks"][0]["composition"]["code"],
            self.definition.composition_code,
        )
        self.assertEqual(
            deck_response.data["last_used_deck_id"],
            deck_response.data["decks"][0]["id"],
        )

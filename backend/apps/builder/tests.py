import yaml
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.collection.models import Deck, DeckCard

from .models import (
    AIPlayer,
    Builder,
    CardTemplate,
    CardTrait,
    Faction,
    HeroTemplate,
    Tag,
    Title,
    TraitOverride,
)
from .schemas import TitleConfig
from .services import IngestionService

User = get_user_model()


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


class BuilderTestCase(TestCase):
    """Test cases for the builder app."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="testuser@example.com", username="testuser"
        )

    def test_builder_app_configured(self):
        """Test that the builder app is properly configured."""
        # This test will pass if the app is properly installed
        self.assertTrue(True)


class TestTitlePermissions(TestCase):
    """Test cases for Title permission methods."""

    def setUp(self):
        """Set up test data."""
        self.author = User.objects.create_user(
            email="author@example.com", username="author"
        )
        self.builder = User.objects.create_user(
            email="builder@example.com", username="builder"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", username="other"
        )

        # Create a draft title
        self.draft_title = Title.objects.create(
            slug="draft-title",
            name="Draft Title",
            author=self.author,
            status=Title.STATUS_DRAFT,
        )

        # Create a published title
        self.published_title = Title.objects.create(
            slug="published-title",
            name="Published Title",
            author=self.author,
            status=Title.STATUS_PUBLISHED,
        )

        # Add builder to draft title
        Builder.objects.create(
            title=self.draft_title, user=self.builder, added_by=self.author
        )

    def test_published_title_viewable_by_anyone(self):
        """Published titles should be viewable by anyone, including anonymous users."""
        self.assertTrue(self.published_title.can_be_viewed_by(self.author))
        self.assertTrue(self.published_title.can_be_viewed_by(self.builder))
        self.assertTrue(self.published_title.can_be_viewed_by(self.other_user))
        self.assertTrue(self.published_title.can_be_viewed_by(None))  # Anonymous

    def test_draft_title_viewable_by_author(self):
        """Draft titles should be viewable by the author."""
        self.assertTrue(self.draft_title.can_be_viewed_by(self.author))

    def test_draft_title_viewable_by_builder(self):
        """Draft titles should be viewable by builders."""
        self.assertTrue(self.draft_title.can_be_viewed_by(self.builder))

    def test_draft_title_not_viewable_by_others(self):
        """Draft titles should not be viewable by other users."""
        self.assertFalse(self.draft_title.can_be_viewed_by(self.other_user))

    def test_draft_title_not_viewable_by_anonymous(self):
        """Draft titles should not be viewable by anonymous users."""
        self.assertFalse(self.draft_title.can_be_viewed_by(None))


class TestTitleAPIPermissions(APITestCase):
    """Test cases for Title API endpoint permissions."""

    def setUp(self):
        """Set up test data."""
        self.author = User.objects.create_user(
            email="author@example.com", username="author"
        )
        self.builder = User.objects.create_user(
            email="builder@example.com", username="builder"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", username="other"
        )

        # Create a draft title
        self.draft_title = Title.objects.create(
            slug="draft-title",
            name="Draft Title",
            author=self.author,
            status=Title.STATUS_DRAFT,
        )

        # Create a published title
        self.published_title = Title.objects.create(
            slug="published-title",
            name="Published Title",
            author=self.author,
            status=Title.STATUS_PUBLISHED,
        )

        # Add builder to draft title
        Builder.objects.create(
            title=self.draft_title, user=self.builder, added_by=self.author
        )

    def test_published_title_accessible_by_anonymous(self):
        """Published titles should be accessible by anonymous users."""
        url = reverse("core:title-by-slug", kwargs={"slug": self.published_title.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Published Title")

    def test_draft_title_forbidden_for_anonymous(self):
        """Draft titles should return 403 for anonymous users."""
        url = reverse("core:title-by-slug", kwargs={"slug": self.draft_title.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_draft_title_accessible_by_author(self):
        """Draft titles should be accessible by the author."""
        self.client.force_authenticate(user=self.author)
        url = reverse("core:title-by-slug", kwargs={"slug": self.draft_title.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Draft Title")

    def test_draft_title_accessible_by_builder(self):
        """Draft titles should be accessible by builders."""
        self.client.force_authenticate(user=self.builder)
        url = reverse("core:title-by-slug", kwargs={"slug": self.draft_title.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Draft Title")

    def test_draft_title_forbidden_for_other_users(self):
        """Draft titles should return 403 for other authenticated users."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse("core:title-by-slug", kwargs={"slug": self.draft_title.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_read_title_config(self):
        self.client.force_authenticate(user=self.author)
        url = reverse("title-config", kwargs={"title_slug": self.draft_title.slug})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["config"]["deck_size_limit"], 30)
        self.assertEqual(response.data["config"]["min_cards_in_deck"], 10)
        self.assertEqual(response.data["config"]["ranked_time_per_turn"], 60)

    def test_builder_can_update_title_config(self):
        self.client.force_authenticate(user=self.builder)
        url = reverse("title-config", kwargs={"title_slug": self.draft_title.slug})

        response = self.client.put(
            url,
            {
                "config": {
                    "deck_size_limit": 40,
                    "min_cards_in_deck": 12,
                    "deck_card_max_count": 3,
                    "hand_start_size": 4,
                    "side_b_compensation": "coin",
                    "death_retaliation": True,
                    "ranked_time_per_turn": 75,
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.draft_title.refresh_from_db()
        self.assertEqual(self.draft_title.config["deck_size_limit"], 40)
        self.assertEqual(self.draft_title.config["min_cards_in_deck"], 12)
        self.assertEqual(self.draft_title.config["deck_card_max_count"], 3)
        self.assertEqual(self.draft_title.config["hand_start_size"], 4)
        self.assertEqual(self.draft_title.config["side_b_compensation"], "coin")
        self.assertTrue(self.draft_title.config["death_retaliation"])
        self.assertEqual(self.draft_title.config["ranked_time_per_turn"], 75)

    def test_other_user_cannot_update_title_config(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("title-config", kwargs={"title_slug": self.draft_title.slug})

        response = self.client.put(
            url,
            {"config": {"deck_size_limit": 40}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_title_config_rejects_min_cards_above_deck_limit(self):
        self.client.force_authenticate(user=self.author)
        url = reverse("title-config", kwargs={"title_slug": self.draft_title.slug})

        response = self.client.put(
            url,
            {
                "config": {
                    "deck_size_limit": 10,
                    "min_cards_in_deck": 11,
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot exceed", response.data["error"])

    def test_author_can_read_title_content_config(self):
        hero = HeroTemplate.objects.create(
            title=self.draft_title,
            slug="warrior",
            name="Warrior",
            description="Front line hero",
            health=30,
            hero_power={"name": "Strike", "cost": 2, "actions": []},
        )
        card = CardTemplate.objects.create(
            title=self.draft_title,
            slug="shield-slam",
            name="Shield Slam",
            description="Hero scoped card",
            card_type=CardTemplate.CARD_TYPE_SPELL,
            cost=2,
        )
        card.allowed_heroes.add(hero)

        self.client.force_authenticate(user=self.author)
        url = reverse(
            "title-content-config", kwargs={"title_slug": self.draft_title.slug}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"]["slug"], self.draft_title.slug)
        self.assertEqual(len(response.data["heroes"]), 1)
        self.assertEqual(response.data["heroes"][0]["slug"], "warrior")
        self.assertEqual(len(response.data["cards"]), 1)
        self.assertEqual(response.data["cards"][0]["slug"], "shield-slam")
        self.assertEqual(response.data["cards"][0]["hero_slugs"], ["warrior"])

    def test_author_can_manage_title_ai_decks(self):
        self.draft_title.config = {
            "deck_size_limit": 10,
            "min_cards_in_deck": 2,
            "deck_card_max_count": 3,
        }
        self.draft_title.save(update_fields=["config"])
        hero = HeroTemplate.objects.create(
            title=self.draft_title,
            slug="warrior",
            name="Warrior",
            description="Front line hero",
            health=30,
            hero_power={"name": "Strike", "cost": 2, "actions": []},
        )
        strike = CardTemplate.objects.create(
            title=self.draft_title,
            slug="strike",
            name="Strike",
            card_type=CardTemplate.CARD_TYPE_SPELL,
            cost=1,
        )
        guard = CardTemplate.objects.create(
            title=self.draft_title,
            slug="guard",
            name="Guard",
            card_type=CardTemplate.CARD_TYPE_CREATURE,
            cost=2,
            attack=1,
            health=3,
        )

        self.client.force_authenticate(user=self.author)
        list_url = reverse(
            "title-ai-decks", kwargs={"title_slug": self.draft_title.slug}
        )
        response = self.client.post(
            list_url,
            {
                "name": "Practice Bot",
                "description": "Editable AI deck",
                "hero_id": hero.id,
                "strategy": "control",
                "is_pve_opponent": True,
                "cards": [
                    {"card_id": strike.id, "count": 1},
                    {"card_id": guard.id, "count": 1},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        deck_id = response.data["id"]
        deck = Deck.objects.get(id=deck_id)
        self.assertIsNone(deck.user_id)
        self.assertIsNotNone(deck.ai_player_id)
        self.assertTrue(deck.is_pve_opponent)
        self.assertEqual(deck.deck_size, 2)
        self.assertEqual(deck.script["strategy"], "control")

        detail_url = reverse(
            "title-ai-deck-detail",
            kwargs={"title_slug": self.draft_title.slug, "deck_id": deck_id},
        )
        response = self.client.patch(
            detail_url,
            {
                "name": "Practice Bot 2",
                "cards": [
                    {"card_id": strike.id, "count": 2},
                    {"card_id": guard.id, "count": 1},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["name"], "Practice Bot 2")
        self.assertEqual(response.data["card_count"], 3)

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            [deck["name"] for deck in response.data["decks"]], ["Practice Bot 2"]
        )

        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        deck.refresh_from_db()
        self.assertIsNotNone(deck.archived_at)

    def test_author_can_manage_ordered_ai_deck_draw_setup(self):
        self.draft_title.config = {
            "deck_size_limit": 10,
            "min_cards_in_deck": 2,
            "deck_card_max_count": 3,
            "hand_start_size": 3,
        }
        self.draft_title.save(update_fields=["config"])
        hero = HeroTemplate.objects.create(
            title=self.draft_title,
            slug="warrior",
            name="Warrior",
            description="Front line hero",
            health=30,
            hero_power={"name": "Strike", "cost": 2, "actions": []},
        )
        strike = CardTemplate.objects.create(
            title=self.draft_title,
            slug="strike",
            name="Strike",
            card_type=CardTemplate.CARD_TYPE_SPELL,
            cost=1,
        )
        guard = CardTemplate.objects.create(
            title=self.draft_title,
            slug="guard",
            name="Guard",
            card_type=CardTemplate.CARD_TYPE_CREATURE,
            cost=2,
            attack=1,
            health=3,
        )

        self.client.force_authenticate(user=self.author)
        list_url = reverse(
            "title-ai-decks", kwargs={"title_slug": self.draft_title.slug}
        )
        response = self.client.post(
            list_url,
            {
                "name": "Ordered Bot",
                "hero_id": hero.id,
                "strategy": "control",
                "draw_mode": "ordered",
                "starting_hand_size": 2,
                "draw_order": [guard.id, strike.id, guard.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["draw_mode"], "ordered")
        self.assertEqual(response.data["starting_hand_size"], 2)
        self.assertEqual(response.data["draw_order"], [guard.id, strike.id, guard.id])
        self.assertEqual(response.data["card_count"], 3)

        deck = Deck.objects.get(id=response.data["id"])
        self.assertEqual(deck.script["draw_order"], [guard.id, strike.id, guard.id])
        self.assertEqual(deck.deckcard_set.get(card=guard).count, 2)
        self.assertEqual(deck.deckcard_set.get(card=strike).count, 1)

        detail_url = reverse(
            "title-ai-deck-detail",
            kwargs={"title_slug": self.draft_title.slug, "deck_id": deck.id},
        )
        response = self.client.patch(
            detail_url,
            {
                "starting_hand_size": 1,
                "draw_order": [strike.id, strike.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["starting_hand_size"], 1)
        self.assertEqual(response.data["draw_order"], [strike.id, strike.id])
        deck.refresh_from_db()
        self.assertFalse(deck.deckcard_set.filter(card=guard).exists())
        self.assertEqual(deck.deckcard_set.get(card=strike).count, 2)

    def test_ai_deck_can_ignore_player_deck_rule_limits(self):
        self.draft_title.config = {
            "deck_size_limit": 3,
            "min_cards_in_deck": 10,
            "deck_card_max_count": 1,
        }
        self.draft_title.save(update_fields=["config"])
        hero = HeroTemplate.objects.create(
            title=self.draft_title,
            slug="warrior",
            name="Warrior",
            description="Front line hero",
            health=30,
            hero_power={"name": "Strike", "cost": 2, "actions": []},
        )
        strike = CardTemplate.objects.create(
            title=self.draft_title,
            slug="strike",
            name="Strike",
            card_type=CardTemplate.CARD_TYPE_SPELL,
            cost=1,
        )
        CardTrait.objects.create(card=strike, trait_slug="unique")

        self.client.force_authenticate(user=self.author)
        list_url = reverse(
            "title-ai-decks", kwargs={"title_slug": self.draft_title.slug}
        )
        response = self.client.post(
            list_url,
            {
                "name": "Draft Bot",
                "hero_id": hero.id,
                "is_pve_opponent": True,
                "cards": [{"card_id": strike.id, "count": 5}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["card_count"], 5)

        detail_url = reverse(
            "title-ai-deck-detail",
            kwargs={
                "title_slug": self.draft_title.slug,
                "deck_id": response.data["id"],
            },
        )
        response = self.client.patch(
            detail_url,
            {"cards": [{"card_id": strike.id, "count": 6}]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["card_count"], 6)

    def test_title_ai_decks_exclude_intro_scenario_decks(self):
        hero = HeroTemplate.objects.create(
            title=self.draft_title,
            slug="warrior",
            name="Warrior",
            description="Front line hero",
            health=30,
            hero_power={"name": "Strike", "cost": 2, "actions": []},
        )
        default_ai = AIPlayer.objects.create(name="Default")
        intro_ai = AIPlayer.objects.create(
            name="Intro Scenario",
            difficulty=AIPlayer.AI_DIFFICULTY_EASY,
        )
        Deck.objects.create(
            ai_player=default_ai,
            title=self.draft_title,
            name="Practice",
            hero=hero,
        )
        Deck.objects.create(
            ai_player=intro_ai,
            title=self.draft_title,
            name="Intro intro-archetype-v1 side_a",
            hero=hero,
            is_pve_opponent=False,
        )

        self.client.force_authenticate(user=self.author)
        url = reverse("title-ai-decks", kwargs={"title_slug": self.draft_title.slug})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            [deck["name"] for deck in response.data["decks"]], ["Practice"]
        )

    def test_other_user_cannot_read_title_ai_decks(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("title-ai-decks", kwargs={"title_slug": self.draft_title.slug})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_export_title_snapshot_without_ids(self):
        HeroTemplate.objects.create(
            title=self.draft_title,
            slug="warrior",
            name="Warrior",
            description="Front line hero",
            health=30,
            hero_power={"name": "Strike", "cost": 2, "actions": []},
        )
        CardTemplate.objects.create(
            title=self.draft_title,
            slug="shield-slam",
            name="Shield Slam",
            description="Hero scoped card",
            card_type=CardTemplate.CARD_TYPE_SPELL,
            cost=2,
        )

        self.client.force_authenticate(user=self.author)
        url = reverse("title-snapshot", kwargs={"title_slug": self.draft_title.slug})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        manifest = yaml.safe_load(response.data["yaml"])
        self.assertEqual(manifest[0]["type"], "title")
        self.assertEqual(manifest[0]["slug"], self.draft_title.slug)
        self.assertFalse(_contains_key(manifest, "id"))
        self.assertIn("cards", response.data["counts"])

    def test_other_user_cannot_read_title_content_config(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse(
            "title-content-config", kwargs={"title_slug": self.draft_title.slug}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_read_hero_yaml(self):
        HeroTemplate.objects.create(
            title=self.draft_title,
            slug="warrior",
            name="Warrior",
            description="Front line hero",
            health=30,
            hero_power={"name": "Strike", "cost": 2, "actions": []},
        )

        self.client.force_authenticate(user=self.author)
        url = reverse(
            "hero-yaml",
            kwargs={"title_slug": self.draft_title.slug, "hero_slug": "warrior"},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = yaml.safe_load(response.data["yaml"])
        self.assertEqual(data["type"], "hero")
        self.assertEqual(data["slug"], "warrior")
        self.assertEqual(data["name"], "Warrior")
        self.assertEqual(data["health"], 30)
        self.assertEqual(data["hero_power"]["name"], "Strike")
        self.assertEqual(data["hero_power"]["cost"], 2)

    def test_other_user_cannot_read_hero_yaml(self):
        HeroTemplate.objects.create(
            title=self.draft_title,
            slug="warrior",
            name="Warrior",
            description="Front line hero",
            health=30,
            hero_power={"name": "Strike", "actions": []},
        )

        self.client.force_authenticate(user=self.other_user)
        url = reverse(
            "hero-yaml",
            kwargs={"title_slug": self.draft_title.slug, "hero_slug": "warrior"},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestCardYamlValidation(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="card-author@example.com", username="card-author"
        )
        self.title = Title.objects.create(
            slug="card-validation",
            name="Card Validation",
            author=self.author,
            status=Title.STATUS_DRAFT,
            is_latest=True,
        )
        self.client.force_authenticate(user=self.author)

    def _invalid_action_yaml(self, *, name="Invalid Spell"):
        return f"""
        name: {name}
        description: Remove abilities from an enemy creature.
        card_type: spell
        cost: 1
        traits:
          - type: battlecry
            actions:
              - action: transmogrify
                target: enemy
                scope: single
        """

    def test_create_card_rejects_invalid_nested_action(self):
        url = reverse("card-create", kwargs={"title_slug": self.title.slug})

        response = self.client.post(
            url,
            {
                "slug": "invalid-action",
                "yaml_definition": self._invalid_action_yaml(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid trait #1", response.data["error"])
        self.assertIn("transmogrify", response.data["error"])
        self.assertFalse(
            CardTemplate.objects.filter(
                title=self.title, slug="invalid-action"
            ).exists()
        )

    def test_update_card_rejects_invalid_nested_action_without_mutating_card(self):
        card = CardTemplate.objects.create(
            title=self.title,
            slug="existing-spell",
            name="Existing Spell",
            description="Safe description.",
            card_type=CardTemplate.CARD_TYPE_SPELL,
            cost=2,
        )
        url = reverse(
            "card-detail",
            kwargs={"title_slug": self.title.slug, "card_slug": card.slug},
        )

        response = self.client.put(
            url,
            {
                "yaml_definition": self._invalid_action_yaml(name="Changed Spell"),
                "bump_version": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid trait #1", response.data["error"])
        card.refresh_from_db()
        self.assertEqual(card.name, "Existing Spell")
        self.assertEqual(card.description, "Safe description.")
        self.assertEqual(card.cost, 2)
        self.assertFalse(card.cardtrait_set.exists())

    def test_create_card_rejects_bulk_list_yaml_with_clear_error(self):
        url = reverse("card-create", kwargs={"title_slug": self.title.slug})
        yaml_definition = """
        - name: Silence
          card_type: spell
          cost: 1
        """

        response = self.client.post(
            url,
            {"slug": "silence", "yaml_definition": yaml_definition},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("single card object", response.data["error"])
        self.assertNotIn("has no attribute", response.data["error"])

    def test_create_card_accepts_silence_action(self):
        url = reverse("card-create", kwargs={"title_slug": self.title.slug})
        yaml_definition = """
        name: Silence
        description: Remove reactive abilities from an enemy creature.
        card_type: spell
        cost: 1
        traits:
          - type: battlecry
            actions:
              - action: silence
                target: enemy
                scope: single
        """

        response = self.client.post(
            url,
            {"slug": "silence", "yaml_definition": yaml_definition},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        card = CardTemplate.objects.get(title=self.title, slug="silence")
        self.assertEqual(
            card.cardtrait_set.get().data,
            {"actions": [{"action": "silence", "target": "enemy", "scope": "single"}]},
        )


class TestIngestion(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com", username="testuser"
        )
        self.title = IngestionService.create_title(
            name="Test Title", slug="test-title", author=self.user
        ).title

    def test_ingest_new_card(self):
        card_yaml = """
        - type: card
          card_type: creature
          slug: small-charge-drawrattle
          name: Small Charge Drawrattle
          description: Charge, draw a card on destruction.
          cost: 2
          attack: 1
          health: 1
          traits:
          - type: charge
          - type: deathrattle
            actions:
            - action: draw
              amount: 1
        """
        self.assertEqual(CardTemplate.objects.count(), 0)

        ingestion_service = IngestionService(self.title)
        ingestion_service.ingest_yaml(card_yaml)

        self.assertEqual(CardTemplate.objects.count(), 1)
        card_template = CardTemplate.objects.first()
        self.assertEqual(card_template.name, "Small Charge Drawrattle")
        self.assertEqual(
            card_template.description, "Charge, draw a card on destruction."
        )
        self.assertEqual(card_template.cost, 2)
        self.assertEqual(card_template.attack, 1)
        self.assertEqual(card_template.health, 1)
        self.assertEqual(card_template.cardtrait_set.count(), 2)
        self.assertEqual(
            card_template.cardtrait_set.filter(trait_slug="charge").count(), 1
        )
        self.assertEqual(
            card_template.cardtrait_set.filter(trait_slug="deathrattle").count(), 1
        )
        card_trait = CardTrait.objects.get(card=card_template, trait_slug="deathrattle")
        self.assertEqual(card_trait.data["actions"][0]["action"], "draw")
        self.assertEqual(card_trait.data["actions"][0]["amount"], 1)

    def test_ingest_triggered_trait_with_event_amount(self):
        card_yaml = """
        - type: card
          card_type: creature
          slug: blood-conduit
          name: Blood Conduit
          description: Heal your hero when damaged.
          cost: 2
          attack: 1
          health: 3
          traits:
          - type: triggered
            when:
              event: damage
              target:
                self: true
            actions:
            - action: heal
              target: hero
              amount:
                event: damage_taken
        """

        ingestion_service = IngestionService(self.title)
        ingestion_service.ingest_yaml(card_yaml)

        card_template = CardTemplate.objects.get(slug="blood-conduit")
        card_trait = CardTrait.objects.get(card=card_template, trait_slug="triggered")
        self.assertEqual(card_trait.data["when"]["event"], "damage")
        self.assertTrue(card_trait.data["when"]["target"]["self"])
        self.assertEqual(card_trait.data["actions"][0]["action"], "heal")
        self.assertEqual(
            card_trait.data["actions"][0]["amount"],
            {"event": "damage_taken"},
        )

        snapshot_yaml = ingestion_service.export_snapshot_yaml()
        manifest = yaml.safe_load(snapshot_yaml)
        card_resource = next(
            resource
            for resource in manifest
            if resource["type"] == "card" and resource["slug"] == "blood-conduit"
        )
        triggered_trait = card_resource["traits"][0]
        self.assertEqual(triggered_trait["type"], "triggered")
        self.assertEqual(triggered_trait["when"]["event"], "damage")
        self.assertEqual(
            triggered_trait["actions"][0]["amount"]["event"], "damage_taken"
        )

    def test_ingest_triggered_trait_with_event_amount_multiplier(self):
        card_yaml = """
        - type: card
          card_type: creature
          slug: pain-cultivator
          name: Pain Cultivator
          description: Grows as friendly creatures deal damage.
          cost: 3
          attack: 2
          health: 4
          traits:
          - type: triggered
            when:
              event: damage
              source:
                kind: creature
                controller: self
            actions:
            - action: buff
              target: self
              attribute: health
              amount:
                event: damage
                multiplier: 0.5
        """

        ingestion_service = IngestionService(self.title)
        ingestion_service.ingest_yaml(card_yaml)

        card_template = CardTemplate.objects.get(slug="pain-cultivator")
        card_trait = CardTrait.objects.get(card=card_template, trait_slug="triggered")
        amount = card_trait.data["actions"][0]["amount"]
        self.assertEqual(amount["event"], "damage")
        self.assertEqual(amount["multiplier"], 0.5)

        snapshot_yaml = ingestion_service.export_snapshot_yaml()
        manifest = yaml.safe_load(snapshot_yaml)
        card_resource = next(
            resource
            for resource in manifest
            if resource["type"] == "card" and resource["slug"] == "pain-cultivator"
        )
        exported_amount = card_resource["traits"][0]["actions"][0]["amount"]
        self.assertEqual(exported_amount["event"], "damage")
        self.assertEqual(exported_amount["multiplier"], 0.5)

    def test_title_config_defaults_min_cards(self):
        config = TitleConfig()
        self.assertEqual(config.min_cards_in_deck, 10)

    def test_ingest_config_updates_min_cards_in_deck(self):
        config_yaml = """
        - type: config
          deck_size_limit: 30
          min_cards_in_deck: 12
          deck_card_max_count: 2
          ranked_time_per_turn: 90
        """

        ingestion_service = IngestionService(self.title)
        ingestion_service.ingest_yaml(config_yaml)

        self.title.refresh_from_db()
        self.assertEqual(self.title.config["min_cards_in_deck"], 12)
        self.assertEqual(self.title.config["ranked_time_per_turn"], 90)

    def test_ingest_card_sets_allowed_heroes(self):
        HeroTemplate.objects.create(
            title=self.title,
            slug="warrior",
            name="Warrior",
            description="Front line hero",
            health=30,
            hero_power={"name": "Strike", "actions": []},
        )
        card_yaml = """
        - type: card
          card_type: spell
          slug: shield-slam
          name: Shield Slam
          description: Warrior only spell.
          cost: 2
          hero_slugs:
          - warrior
        """

        ingestion_service = IngestionService(self.title)
        ingestion_service.ingest_yaml(card_yaml)

        card_template = CardTemplate.objects.get(slug="shield-slam")
        self.assertEqual(
            list(card_template.allowed_heroes.values_list("slug", flat=True)),
            ["warrior"],
        )

    def test_snapshot_export_includes_slug_based_title_resources(self):
        faction = Faction.objects.create(
            title=self.title,
            slug="guard",
            name="Guard",
            description="Defensive faction",
        )
        tag = Tag.objects.create(
            title=self.title,
            slug="starter",
            name="Starter",
            description="Starter content",
        )
        TraitOverride.objects.create(
            title=self.title,
            slug="taunt",
            name="Guard",
            description="Must be attacked first.",
        )
        hero = HeroTemplate.objects.create(
            title=self.title,
            slug="warrior",
            name="Warrior",
            description="Front line hero",
            health=30,
            hero_power={"name": "Strike", "actions": []},
            faction=faction,
            spec={"armor": 1},
        )
        card = CardTemplate.objects.create(
            title=self.title,
            slug="shield-slam",
            name="Shield Slam",
            description="Hero scoped card.",
            card_type=CardTemplate.CARD_TYPE_SPELL,
            cost=2,
            faction=faction,
            spec={"rarity": "common"},
        )
        card.tags.add(tag)
        card.allowed_heroes.add(hero)
        CardTrait.objects.create(
            card=card,
            trait_slug="battlecry",
            data={"actions": [{"action": "damage", "amount": 1}]},
        )
        deck = Deck.objects.create(
            ai_player=IngestionService(self.title).get_default_ai_player(),
            title=self.title,
            name="Starter Deck",
            description="AI starter deck",
            hero=hero,
            script={"strategy": "control"},
        )
        DeckCard.objects.create(deck=deck, card=card, count=2)

        snapshot_yaml = IngestionService(self.title).export_snapshot_yaml()
        manifest = yaml.safe_load(snapshot_yaml)
        resources_by_type = {resource["type"]: resource for resource in manifest}

        self.assertFalse(_contains_key(manifest, "id"))
        self.assertEqual(resources_by_type["title"]["slug"], self.title.slug)
        self.assertEqual(resources_by_type["faction"]["slug"], "guard")
        self.assertEqual(resources_by_type["tag"]["slug"], "starter")
        self.assertEqual(resources_by_type["trait_override"]["slug"], "taunt")
        self.assertEqual(resources_by_type["hero"]["spec"], {"armor": 1})
        self.assertEqual(resources_by_type["card"]["hero_slugs"], ["warrior"])
        self.assertEqual(resources_by_type["card"]["tags"], ["starter"])
        self.assertNotIn("deck", resources_by_type)

    def test_snapshot_import_updates_by_slug_and_preserves_ids(self):
        faction = Faction.objects.create(
            title=self.title,
            slug="guard",
            name="Old Guard",
        )
        hero = HeroTemplate.objects.create(
            title=self.title,
            slug="warrior",
            name="Old Warrior",
            description="Old hero",
            health=10,
            hero_power={"name": "Old", "actions": []},
        )
        card = CardTemplate.objects.create(
            title=self.title,
            slug="shield-slam",
            name="Old Shield Slam",
            description="Old card.",
            card_type=CardTemplate.CARD_TYPE_SPELL,
            cost=9,
        )
        existing_card_id = card.id
        snapshot_yaml = """
        - type: title
          slug: test-title
          name: Snapshot Title
          description: Imported snapshot
        - type: config
          deck_size_limit: 30
          min_cards_in_deck: 12
          deck_card_max_count: 2
          hand_start_size: 4
          ranked_time_per_turn: 90
        - type: faction
          slug: guard
          name: Guard
          description: Defensive faction
        - type: tag
          slug: starter
          name: Starter
        - type: trait_override
          slug: taunt
          name: Guard
          description: Must be attacked first.
        - type: hero
          slug: warrior
          name: Warrior
          description: Front line hero
          health: 30
          faction: guard
          spec:
            armor: 1
          hero_power:
            name: Strike
            cost: 2
            actions: []
        - type: card
          card_type: spell
          slug: shield-slam
          name: Shield Slam
          description: Warrior only spell.
          cost: 2
          faction: guard
          spec:
            rarity: common
          tags:
          - starter
          hero_slugs:
          - warrior
          traits:
          - type: taunt
        - type: deck
          slug: starter-deck
          name: Starter Deck
          description: AI starter deck
          hero: warrior
          script:
            strategy: control
          cards:
          - card: shield-slam
            count: 2
        """

        ingested, removed = IngestionService(self.title).import_snapshot_yaml(
            snapshot_yaml
        )

        self.assertEqual(removed, [])
        self.assertEqual(len(ingested), 7)
        self.title.refresh_from_db()
        self.assertEqual(self.title.name, "Snapshot Title")
        self.assertEqual(self.title.config["min_cards_in_deck"], 12)
        faction.refresh_from_db()
        self.assertEqual(faction.name, "Guard")
        hero.refresh_from_db()
        self.assertEqual(hero.name, "Warrior")
        self.assertEqual(hero.faction.slug, "guard")
        self.assertEqual(hero.spec, {"armor": 1})
        self.assertEqual(hero.hero_power["cost"], 2)
        card.refresh_from_db()
        self.assertEqual(card.id, existing_card_id)
        self.assertEqual(card.name, "Shield Slam")
        self.assertEqual(card.cost, 2)
        self.assertEqual(card.faction.slug, "guard")
        self.assertEqual(card.spec, {"rarity": "common"})
        self.assertEqual(list(card.tags.values_list("slug", flat=True)), ["starter"])
        self.assertEqual(
            list(card.allowed_heroes.values_list("slug", flat=True)), ["warrior"]
        )
        self.assertEqual(card.cardtrait_set.get().trait_slug, "taunt")
        self.assertFalse(
            Deck.objects.filter(title=self.title, name="Starter Deck").exists()
        )

    def test_replace_snapshot_deactivates_missing_latest_templates(self):
        old_hero = HeroTemplate.objects.create(
            title=self.title,
            slug="old-hero",
            name="Old Hero",
            description="Removed from snapshot",
            health=20,
            hero_power={"name": "Old", "actions": []},
        )
        old_card = CardTemplate.objects.create(
            title=self.title,
            slug="old-card",
            name="Old Card",
            description="Removed from snapshot",
            card_type=CardTemplate.CARD_TYPE_CREATURE,
            cost=1,
            attack=1,
            health=1,
        )
        deck = Deck.objects.create(
            ai_player=IngestionService(self.title).get_default_ai_player(),
            title=self.title,
            name="Practice",
            hero=old_hero,
        )
        DeckCard.objects.create(deck=deck, card=old_card, count=1)
        snapshot_yaml = """
        - type: title
          slug: test-title
          name: Test Title
          description: Snapshot
        - type: config
          deck_size_limit: 30
          min_cards_in_deck: 10
          deck_card_max_count: 9
          hand_start_size: 3
          ranked_time_per_turn: 60
        - type: hero
          slug: warrior
          name: Warrior
          description: Front line hero
          health: 30
          hero_power:
            name: Strike
            actions: []
        - type: card
          card_type: creature
          slug: footman
          name: Footman
          description: Basic unit.
          cost: 1
          attack: 1
          health: 2
        """

        _ingested, removed = IngestionService(self.title).import_snapshot_yaml(
            snapshot_yaml, replace_missing=True
        )

        old_card.refresh_from_db()
        self.assertFalse(old_card.is_latest)
        self.assertFalse(
            HeroTemplate.objects.get(title=self.title, slug="old-hero").is_latest
        )
        self.assertTrue(
            CardTemplate.objects.get(title=self.title, slug="footman").is_latest
        )
        self.assertTrue(Deck.objects.filter(id=deck.id).exists())
        self.assertEqual(
            {(resource["resource_type"], resource["slug"]) for resource in removed},
            {("card", "old-card"), ("hero", "old-hero")},
        )

    def test_replace_snapshot_rejects_partial_manifests(self):
        with self.assertRaisesMessage(
            ValueError, "Replace imports require a full title snapshot"
        ):
            IngestionService(self.title).import_snapshot_yaml(
                """
                - type: card
                  card_type: creature
                  slug: footman
                  name: Footman
                  cost: 1
                  attack: 1
                  health: 2
                """,
                replace_missing=True,
            )


# API Test examples for when you implement models and views:

# class ProjectAPITestCase(APITestCase):
#     """Test cases for Project API endpoints."""
#
#     def setUp(self):
#         """Set up test data."""
#         self.user = User.objects.create_user(
#             email="testuser@example.com",
#             username="testuser"
#         )
#         self.project = Project.objects.create(
#             name="Test Project",
#             description="A test project",
#             owner=self.user
#         )
#
#     def test_create_project(self):
#         """Test creating a new project."""
#         self.client.force_authenticate(user=self.user)
#         url = reverse('project-list')
#         data = {
#             'name': 'New Project',
#             'description': 'A new test project'
#         }
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(Project.objects.count(), 2)
#
#     def test_list_user_projects(self):
#         """Test listing projects for authenticated user."""
#         self.client.force_authenticate(user=self.user)
#         url = reverse('project-list')
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data['results']), 1)
#
#     def test_unauthorized_access(self):
#         """Test that unauthenticated users cannot access projects."""
#         url = reverse('project-list')
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

# class CanvasAPITestCase(APITestCase):
#     """Test cases for Canvas API endpoints."""
#
#     def setUp(self):
#         """Set up test data."""
#         self.user = User.objects.create_user(
#             email="testuser@example.com",
#             username="testuser"
#         )
#         self.project = Project.objects.create(
#             name="Test Project",
#             owner=self.user
#         )
#         self.canvas = Canvas.objects.create(
#             name="Test Canvas",
#             project=self.project,
#             width=800,
#             height=600
#         )
#
#     def test_save_canvas_data(self):
#         """Test saving canvas drawing data."""
#         self.client.force_authenticate(user=self.user)
#         url = reverse('canvas-save-data', kwargs={'pk': self.canvas.pk})
#         data = {
#             'data': {
#                 'shapes': [
#                     {
#                         'type': 'rectangle', 'x': 10, 'y': 10,
#                         'width': 100, 'height': 50,
#                     }
#                 ]
#             }
#         }
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#         # Refresh from database and check data was saved
#         self.canvas.refresh_from_db()
#         self.assertIn('shapes', self.canvas.data)

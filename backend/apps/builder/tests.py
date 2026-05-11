from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Builder, CardTemplate, CardTrait, HeroTemplate, Title
from .schemas import TitleConfig
from .services import IngestionService

User = get_user_model()


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
            hero_power={"name": "Strike", "actions": []},
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

    def test_other_user_cannot_read_title_content_config(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse(
            "title-content-config", kwargs={"title_slug": self.draft_title.slug}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


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
#                     {'type': 'rectangle', 'x': 10, 'y': 10, 'width': 100, 'height': 50}
#                 ]
#             }
#         }
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#         # Refresh from database and check data was saved
#         self.canvas.refresh_from_db()
#         self.assertIn('shapes', self.canvas.data)

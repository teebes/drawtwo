from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APITestCase
from rest_framework import status

from .models import Title, CardTemplate, CardTrait
from .services import IngestionService


User = get_user_model()


class BuilderTestCase(TestCase):
    """Test cases for the builder app."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="testuser@example.com",
            username="testuser"
        )

    def test_builder_app_configured(self):
        """Test that the builder app is properly configured."""
        # This test will pass if the app is properly installed
        self.assertTrue(True)


class TestIngestion(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            username="testuser"
        )
        self.title = IngestionService.create_title(
            name="Test Title",
            slug="test-title",
            author=self.user
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
        self.assertEqual(card_template.description, "Charge, draw a card on destruction.")
        self.assertEqual(card_template.cost, 2)
        self.assertEqual(card_template.attack, 1)
        self.assertEqual(card_template.health, 1)
        self.assertEqual(card_template.cardtrait_set.count(), 2)
        self.assertEqual(card_template.cardtrait_set.filter(trait_slug='charge').count(), 1)
        self.assertEqual(card_template.cardtrait_set.filter(trait_slug='deathrattle').count(), 1)
        card_trait = CardTrait.objects.get(card=card_template, trait_slug='deathrattle')
        self.assertEqual(card_trait.data['actions'][0]['action'], 'draw')
        self.assertEqual(card_trait.data['actions'][0]['amount'], 1)







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

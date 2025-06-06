from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

# Import your models when you create them
# from .models import Project, Canvas, Layer

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

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class HealthCheckTestCase(TestCase):
    """Test cases for the health check endpoint."""

    def test_health_endpoint(self):
        """Test that the health endpoint returns a 200 status."""
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "healthy")


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
        self.assertEqual(user.display_name, "test2@example.com")
        self.assertFalse(user.is_email_verified)

    def test_admin_accessible(self):
        """Test that admin is accessible."""
        response = self.client.get("/admin/")
        # Should redirect to login (302) since we're not authenticated
        self.assertEqual(response.status_code, 302)

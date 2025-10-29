"""
Tests for the authentication app.

This comprehensive test suite covers:
- User model functionality (creation, uniqueness, properties)
- API endpoints (registration, login, validation, protected access)
- Email confirmation flow (including edge cases and error conditions)
- Profile management (get/update profile, username conflicts)
- Integration tests (complete user journey from signup to authenticated access)

Total tests: 29 (5 model tests + 24 API/integration tests)
"""

from unittest.mock import patch

from allauth.account.models import EmailAddress, EmailConfirmation
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserModelTestCase(TestCase):
    """Test cases for the custom User model."""

    def test_create_user_with_email_only(self):
        """Test creating a user with just email."""
        user = User.objects.create_user(email="test@example.com")
        self.assertEqual(user.email, "test@example.com")
        self.assertIsNone(user.username)
        self.assertEqual(user.display_name, "test@example.com")
        self.assertFalse(user.is_email_verified)
        self.assertFalse(user.has_usable_password())

    def test_create_user_with_username(self):
        """Test creating a user with email and username."""
        user = User.objects.create_user(email="test@example.com", username="testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.display_name, "testuser")
        self.assertFalse(user.is_email_verified)

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            email="admin@example.com", password="testpass123"
        )
        self.assertEqual(user.email, "admin@example.com")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("testpass123"))

    def test_username_uniqueness(self):
        """Test that usernames must be unique when provided."""
        User.objects.create_user(email="user1@example.com", username="uniqueuser")

        # Same username should fail
        with self.assertRaises(Exception):
            User.objects.create_user(email="user2@example.com", username="uniqueuser")

    def test_email_uniqueness(self):
        """Test that emails must be unique."""
        User.objects.create_user(email="unique@example.com")

        # Same email should fail
        with self.assertRaises(Exception):
            User.objects.create_user(email="unique@example.com")

    def test_str_representation(self):
        """Test string representation of user."""
        user_with_username = User.objects.create_user(
            email="test@example.com", username="testuser"
        )
        user_without_username = User.objects.create_user(email="nouser@example.com")

        self.assertEqual(str(user_with_username), "testuser")
        self.assertEqual(str(user_without_username), "nouser@example.com")


class AuthenticationAPITestCase(APITestCase):
    """Test cases for authentication API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.register_url = reverse("authentication:register")
        self.passwordless_login_url = reverse("authentication:passwordless_login")
        self.email_confirm_url = reverse("authentication:email_confirm")
        self.protected_test_url = reverse("authentication:protected_test")

    def test_register_with_email_only(self):
        """Test user registration with just email (minimal friction)."""
        data = {"email": "minimal@example.com"}
        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        self.assertIn("user", response.data)

        user_data = response.data["user"]
        self.assertEqual(user_data["email"], "minimal@example.com")
        self.assertIsNone(user_data["username"])
        self.assertEqual(user_data["display_name"], "minimal@example.com")
        self.assertFalse(user_data["is_email_verified"])

        # Verify user was created in database
        user = User.objects.get(email="minimal@example.com")
        self.assertEqual(user.email, "minimal@example.com")
        self.assertIsNone(user.username)

    def test_register_with_email_and_username(self):
        """Test user registration with email and optional username."""
        data = {"email": "gamer@example.com", "username": "progamer123"}
        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user_data = response.data["user"]
        self.assertEqual(user_data["email"], "gamer@example.com")
        self.assertEqual(user_data["username"], "progamer123")
        self.assertEqual(user_data["display_name"], "progamer123")

        # Verify user was created in database
        user = User.objects.get(email="gamer@example.com")
        self.assertEqual(user.username, "progamer123")

    def test_register_duplicate_email(self):
        """Test that duplicate email registration fails."""
        # Create first user
        User.objects.create_user(email="existing@example.com")

        # Try to register with same email
        data = {"email": "existing@example.com"}
        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        """Test that duplicate username registration fails."""
        # Create first user with username
        User.objects.create_user(email="user1@example.com", username="takenname")

        # Try to register with same username
        data = {"email": "user2@example.com", "username": "takenname"}
        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_register_empty_username_is_allowed(self):
        """Test that empty username is converted to None."""
        data = {"email": "empty@example.com", "username": ""}
        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_data = response.data["user"]
        self.assertIsNone(user_data["username"])

    def test_passwordless_login_existing_user(self):
        """Test passwordless login for existing user."""
        # Create a user
        User.objects.create_user(email="existing@example.com")

        # Request login email
        data = {"email": "existing@example.com"}
        response = self.client.post(self.passwordless_login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertIn("email", response.data)

    def test_passwordless_login_nonexistent_user(self):
        """Test passwordless login for non-existent user."""
        data = {"email": "nonexistent@example.com"}
        response = self.client.post(self.passwordless_login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_protected_endpoint_without_auth(self):
        """Test that protected endpoint requires authentication."""
        response = self.client.get(self.protected_test_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("apps.authentication.views.send_mail")
    def test_email_confirmation_flow(self, mock_send_mail):
        """Test the complete email confirmation flow."""
        # Register a user
        data = {"email": "confirm@example.com"}
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # User should exist but not be verified
        user = User.objects.get(email="confirm@example.com")
        self.assertFalse(user.is_email_verified)

        # Send passwordless login email
        login_data = {"email": "confirm@example.com"}
        response = self.client.post(
            self.passwordless_login_url, login_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Mock should have been called to send email
        mock_send_mail.assert_called()

        # Get the confirmation key from the email confirmation
        email_address = EmailAddress.objects.get(email="confirm@example.com")
        confirmation = EmailConfirmation.objects.filter(
            email_address=email_address
        ).first()
        self.assertIsNotNone(confirmation)

        # Confirm email with the key
        confirm_data = {"key": confirmation.key}
        response = self.client.post(self.email_confirm_url, confirm_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should return JWT tokens
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)

        # User should now be verified
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_email_confirmation_invalid_key(self):
        """Test email confirmation with invalid key."""
        data = {"key": "invalid-key-12345"}
        response = self.client.post(self.email_confirm_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_confirmation_missing_key(self):
        """Test email confirmation with missing key parameter."""
        data = {}
        response = self.client.post(self.email_confirm_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("key", response.data)

    def test_email_confirmation_empty_key(self):
        """Test email confirmation with empty key."""
        data = {"key": ""}
        response = self.client.post(self.email_confirm_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_confirmation_null_key(self):
        """Test email confirmation with null key."""
        data = {"key": None}
        response = self.client.post(self.email_confirm_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_confirmation_key_with_newlines(self):
        """Test email confirmation with key containing newlines (should fail)."""
        # This tests the bug we just fixed where keys can get corrupted with newlines
        data = {"key": "somekey\nwithbreaks"}
        response = self.client.post(self.email_confirm_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Should return EmailConfirmation.DoesNotExist error
        self.assertIn("error", response.data)

    def test_email_confirmation_wrong_method(self):
        """Test email confirmation with wrong HTTP method."""
        data = {"key": "some-key"}
        response = self.client.get(self.email_confirm_url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_email_confirmation_debug_flow(self):
        """Test email confirmation with detailed debugging to match frontend scenario."""
        # Register a user first
        register_data = {"email": "debug@example.com"}
        response = self.client.post(self.register_url, register_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Send passwordless login email
        login_data = {"email": "debug@example.com"}
        response = self.client.post(
            self.passwordless_login_url, login_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get the confirmation object and key
        email_address = EmailAddress.objects.get(email="debug@example.com")
        confirmation = EmailConfirmation.objects.filter(
            email_address=email_address
        ).first()
        self.assertIsNotNone(confirmation)

        # Debug info - uncomment if needed for debugging test failures
        # print(f"Debug - Confirmation key: {confirmation.key}")
        # print(f"Debug - Key length: {len(confirmation.key)}")
        # print(f"Debug - Key type: {type(confirmation.key)}")

        # Try the exact same request as frontend
        confirm_data = {"key": confirmation.key}
        # print(f"Debug - Request data: {confirm_data}")

        response = self.client.post(self.email_confirm_url, confirm_data, format="json")
        # print(f"Debug - Response status: {response.status_code}")
        # print(f"Debug - Response data: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)

    def test_api_serializer_validation(self):
        """Test API input validation."""
        # Test invalid email format
        data = {"email": "not-an-email"}
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test missing email
        data = {"username": "someuser"}
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test username too long
        data = {"email": "test@example.com", "username": "x" * 151}
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserProfileAPITestCase(APITestCase):
    """Test cases for user profile API."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="profile@example.com", username="profileuser"
        )
        self.profile_url = reverse("authentication:user_profile")

    def test_get_user_profile_authenticated(self):
        """Test getting user profile when authenticated."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "profile@example.com")
        self.assertEqual(response.data["username"], "profileuser")
        self.assertEqual(response.data["display_name"], "profileuser")

    def test_get_user_profile_unauthenticated(self):
        """Test getting user profile when not authenticated."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_user_profile(self):
        """Test updating user profile."""
        self.client.force_authenticate(user=self.user)

        data = {"username": "newusername"}
        response = self.client.patch(self.profile_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "newusername")

        # Verify in database
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "newusername")

    def test_update_profile_duplicate_username(self):
        """Test updating profile with duplicate username fails."""
        # Create another user with username
        User.objects.create_user(email="other@example.com", username="taken")

        self.client.force_authenticate(user=self.user)
        data = {"username": "taken"}
        response = self.client.patch(self.profile_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AuthenticationIntegrationTestCase(APITestCase):
    """Integration tests for the complete authentication flow."""

    def test_complete_signup_and_login_flow(self):
        """Test the complete user journey from signup to authenticated access."""
        # 1. User registers with minimal info
        register_data = {"email": "journey@example.com"}
        response = self.client.post(
            reverse("authentication:register"), register_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 2. User requests login email
        login_data = {"email": "journey@example.com"}
        response = self.client.post(
            reverse("authentication:passwordless_login"), login_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 3. Simulate email confirmation (get the key)
        user = User.objects.get(email="journey@example.com")
        email_address = EmailAddress.objects.get(email="journey@example.com")
        confirmation = EmailConfirmation.objects.filter(
            email_address=email_address
        ).first()

        # 4. User clicks email link (confirms email)
        confirm_data = {"key": confirmation.key}
        response = self.client.post(
            reverse("authentication:email_confirm"), confirm_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should get tokens
        access_token = response.data["access"]
        self.assertIsNotNone(access_token)

        # 5. Use token to access protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(reverse("authentication:protected_test"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 6. User updates profile to add username
        profile_data = {"username": "journeyuser"}
        response = self.client.patch(
            reverse("authentication:user_profile"), profile_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify user is fully set up
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        self.assertEqual(user.username, "journeyuser")
        self.assertEqual(user.display_name, "journeyuser")

    def test_minimal_friction_vs_full_setup(self):
        """Test that both minimal and full user setups work."""
        # Minimal setup (just email)
        minimal_data = {"email": "minimal@example.com"}
        response = self.client.post(
            reverse("authentication:register"), minimal_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Full setup (email + username)
        full_data = {"email": "full@example.com", "username": "fulluser"}
        response = self.client.post(
            reverse("authentication:register"), full_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Both users should exist with appropriate data
        minimal_user = User.objects.get(email="minimal@example.com")
        full_user = User.objects.get(email="full@example.com")

        self.assertIsNone(minimal_user.username)
        self.assertEqual(minimal_user.display_name, "minimal@example.com")

        self.assertEqual(full_user.username, "fulluser")
        self.assertEqual(full_user.display_name, "fulluser")

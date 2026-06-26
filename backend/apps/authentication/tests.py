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
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.control.models import SiteSettings

User = get_user_model()


class UserModelTestCase(TestCase):
    """Test cases for the custom User model."""

    def test_create_user_with_email_only(self):
        """Test creating a user with just email."""
        user = User.objects.create_user(email="test@example.com")
        self.assertEqual(user.email, "test@example.com")
        self.assertIsNone(user.username)
        self.assertEqual(user.display_name, f"Gamer {user.id}")
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
        cache.clear()
        self.register_url = reverse("authentication:register")
        self.passwordless_login_url = reverse("authentication:passwordless_login")
        self.email_confirm_url = reverse("authentication:email_confirm")
        self.google_native_login_url = reverse("authentication:google_native_login")
        self.apple_login_url = reverse("authentication:apple_login")
        self.apple_link_url = reverse("authentication:apple_link")
        self.protected_test_url = reverse("authentication:protected_test")

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_register_with_email_only(self):
        """Test user registration with just email (minimal friction)."""
        data = {"email": "minimal@example.com"}
        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        self.assertIn("user", response.data)

        # Verify user was created in database
        user = User.objects.get(email="minimal@example.com")
        self.assertEqual(user.email, "minimal@example.com")
        self.assertIsNone(user.username)

        user_data = response.data["user"]
        self.assertEqual(user_data["email"], "minimal@example.com")
        self.assertIsNone(user_data["username"])
        self.assertEqual(user_data["display_name"], f"Gamer {user.id}")
        self.assertFalse(user_data["is_email_verified"])

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

    @override_settings(
        FRONTEND_EMAIL_CONFIRM_URL="https://drawtwo.test/auth/email-confirm"
    )
    @patch("apps.authentication.views.send_mail")
    def test_passwordless_login_web_uses_browser_confirm_link(self, mock_send_mail):
        """Web login requests keep the existing browser-confirm link."""
        User.objects.create_user(email="web-link@example.com")

        response = self.client.post(
            self.passwordless_login_url,
            {"email": "web-link@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        email_address = EmailAddress.objects.get(email="web-link@example.com")
        confirmation = EmailConfirmation.objects.get(email_address=email_address)
        message = mock_send_mail.call_args.kwargs["message"]

        self.assertIn(
            f"https://drawtwo.test/auth/email-confirm/{confirmation.key}",
            message,
        )
        self.assertNotIn("/app/login/", message)
        self.assertNotIn("drawtwo://", message)

    @override_settings(
        IOS_APP_LOGIN_URL="https://drawtwo.test/app/login",
        IOS_LOGIN_URL_SCHEME="drawtwo://login",
    )
    @patch("apps.authentication.views.send_mail")
    def test_passwordless_login_ios_uses_app_login_links(self, mock_send_mail):
        """iOS login requests receive app-targeted links and a paste fallback."""
        User.objects.create_user(email="ios-link@example.com")

        response = self.client.post(
            self.passwordless_login_url,
            {"email": "ios-link@example.com", "client": "ios"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        email_address = EmailAddress.objects.get(email="ios-link@example.com")
        confirmation = EmailConfirmation.objects.get(email_address=email_address)
        message = mock_send_mail.call_args.kwargs["message"]

        self.assertIn(f"https://drawtwo.test/app/login/{confirmation.key}", message)
        self.assertIn(f"drawtwo://login/{confirmation.key}", message)
        self.assertIn(confirmation.key, message)
        self.assertNotIn("/auth/email-confirm/", message)

    @override_settings(
        GOOGLE_OAUTH2_CLIENT_ID="server-client-id.apps.googleusercontent.com"
    )
    @patch("apps.authentication.views.google_id_token.verify_oauth2_token")
    def test_google_native_login_creates_verified_user(self, mock_verify_token):
        """Native Google login creates a verified user and returns JWTs."""
        mock_verify_token.return_value = {
            "sub": "google-native-user",
            "email": "native-google@example.com",
            "email_verified": True,
            "picture": "https://example.com/avatar.png",
        }

        response = self.client.post(
            self.google_native_login_url,
            {"id_token": "valid-google-id-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "native-google@example.com")

        user = User.objects.get(email="native-google@example.com")
        self.assertTrue(user.is_email_verified)
        self.assertEqual(user.avatar, "https://example.com/avatar.png")

        email_address = EmailAddress.objects.get(email="native-google@example.com")
        self.assertTrue(email_address.verified)
        self.assertTrue(email_address.primary)
        social_account = SocialAccount.objects.get(provider="google")
        self.assertEqual(social_account.uid, "google-native-user")
        self.assertEqual(social_account.user, user)
        mock_verify_token.assert_called_once()

    @override_settings(
        GOOGLE_OAUTH2_CLIENT_ID="server-client-id.apps.googleusercontent.com"
    )
    @patch("apps.authentication.views.google_id_token.verify_oauth2_token")
    def test_google_native_login_rejects_invalid_token(self, mock_verify_token):
        """Native Google login rejects tokens that fail Google verification."""
        mock_verify_token.side_effect = ValueError("bad token")

        response = self.client.post(
            self.google_native_login_url,
            {"id_token": "invalid-google-id-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @override_settings(
        GOOGLE_OAUTH2_CLIENT_ID="server-client-id.apps.googleusercontent.com"
    )
    @patch("apps.authentication.views.google_id_token.verify_oauth2_token")
    def test_google_native_login_respects_disabled_signups(self, mock_verify_token):
        """Native Google login cannot create new users when signup is disabled."""
        site_settings = SiteSettings.get_settings()
        site_settings.signup_disabled = True
        site_settings.save()

        mock_verify_token.return_value = {
            "email": "blocked-google@example.com",
            "email_verified": True,
        }

        response = self.client.post(
            self.google_native_login_url,
            {"id_token": "valid-google-id-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            User.objects.filter(email="blocked-google@example.com").exists()
        )

    @override_settings(
        APPLE_SIGN_IN_WEB_CLIENT_ID="com.morelsoft.drawtwo.dev.web",
        APPLE_SIGN_IN_IOS_CLIENT_ID="com.morelsoft.drawtwo.dev",
    )
    @patch("apps.authentication.views.verify_apple_identity_token")
    def test_apple_login_creates_verified_user(self, mock_verify_token):
        """Apple login creates a verified user and returns JWTs."""
        mock_verify_token.return_value = {
            "sub": "apple-user-123",
            "aud": "com.morelsoft.drawtwo.dev",
            "email": "native-apple@example.com",
            "email_verified": "true",
        }

        response = self.client.post(
            self.apple_login_url,
            {"identity_token": "valid-apple-identity-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "native-apple@example.com")

        user = User.objects.get(email="native-apple@example.com")
        self.assertTrue(user.is_email_verified)

        email_address = EmailAddress.objects.get(email="native-apple@example.com")
        self.assertTrue(email_address.verified)
        self.assertTrue(email_address.primary)

        social_account = SocialAccount.objects.get(provider="apple")
        self.assertEqual(social_account.uid, "apple-user-123")
        self.assertEqual(social_account.user, user)
        mock_verify_token.assert_called_once_with("valid-apple-identity-token")

    @override_settings(
        APPLE_SIGN_IN_WEB_CLIENT_ID="com.morelsoft.drawtwo.dev.web",
        APPLE_SIGN_IN_IOS_CLIENT_ID="com.morelsoft.drawtwo.dev",
    )
    @patch("apps.authentication.views.exchange_apple_authorization_code")
    @patch("apps.authentication.views.verify_apple_identity_token")
    def test_apple_login_stores_refresh_token_when_authorization_code_is_available(
        self, mock_verify_token, mock_exchange_code
    ):
        """Apple login stores a refresh token so the account can be revoked later."""
        mock_verify_token.return_value = {
            "sub": "apple-user-token",
            "aud": "com.morelsoft.drawtwo.dev",
            "email": "apple-token@example.com",
            "email_verified": "true",
        }
        mock_exchange_code.return_value = {
            "refresh_token": "apple-refresh-token",
        }

        response = self.client.post(
            self.apple_login_url,
            {
                "identity_token": "valid-apple-identity-token",
                "authorization_code": "apple-authorization-code",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        social_account = SocialAccount.objects.get(provider="apple")
        self.assertEqual(
            social_account.extra_data["apple_client_id"],
            "com.morelsoft.drawtwo.dev",
        )
        self.assertEqual(
            social_account.extra_data["apple_refresh_token"],
            "apple-refresh-token",
        )
        mock_exchange_code.assert_called_once_with(
            client_id="com.morelsoft.drawtwo.dev",
            authorization_code="apple-authorization-code",
            redirect_uri=None,
        )

    @override_settings(
        APPLE_SIGN_IN_WEB_CLIENT_ID="com.morelsoft.drawtwo.dev.web",
        APPLE_SIGN_IN_IOS_CLIENT_ID="com.morelsoft.drawtwo.dev",
    )
    @patch("apps.authentication.views.verify_apple_identity_token")
    def test_apple_login_uses_linked_account_without_email(self, mock_verify_token):
        """Apple login can reuse a linked account when Apple omits email."""
        user = User.objects.create_user(email="linked-apple@example.com")
        SocialAccount.objects.create(
            user=user,
            provider="apple",
            uid="apple-user-456",
        )
        mock_verify_token.return_value = {
            "sub": "apple-user-456",
            "aud": "com.morelsoft.drawtwo.dev",
        }

        response = self.client.post(
            self.apple_login_url,
            {"id_token": "valid-apple-identity-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "linked-apple@example.com")

    @override_settings(
        APPLE_SIGN_IN_WEB_CLIENT_ID="com.morelsoft.drawtwo.dev.web",
        APPLE_SIGN_IN_IOS_CLIENT_ID="com.morelsoft.drawtwo.dev",
    )
    @patch("apps.authentication.views.verify_apple_identity_token")
    def test_apple_login_rejects_invalid_token(self, mock_verify_token):
        """Apple login rejects tokens that fail Apple verification."""
        mock_verify_token.side_effect = ValueError("bad token")

        response = self.client.post(
            self.apple_login_url,
            {"identity_token": "invalid-apple-identity-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @override_settings(
        APPLE_SIGN_IN_WEB_CLIENT_ID="com.morelsoft.drawtwo.dev.web",
        APPLE_SIGN_IN_IOS_CLIENT_ID="com.morelsoft.drawtwo.dev",
    )
    @patch("apps.authentication.views.verify_apple_identity_token")
    def test_apple_login_respects_disabled_signups(self, mock_verify_token):
        """Apple login cannot create new users when signup is disabled."""
        site_settings = SiteSettings.get_settings()
        site_settings.signup_disabled = True
        site_settings.save()

        mock_verify_token.return_value = {
            "sub": "apple-user-blocked",
            "aud": "com.morelsoft.drawtwo.dev",
            "email": "blocked-apple@example.com",
            "email_verified": "true",
        }

        response = self.client.post(
            self.apple_login_url,
            {"identity_token": "valid-apple-identity-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            User.objects.filter(email="blocked-apple@example.com").exists()
        )

    @override_settings(
        APPLE_SIGN_IN_WEB_CLIENT_ID="com.morelsoft.drawtwo.dev.web",
        APPLE_SIGN_IN_IOS_CLIENT_ID="com.morelsoft.drawtwo.dev",
    )
    @patch("apps.authentication.views.verify_apple_identity_token")
    def test_apple_link_connects_authenticated_user(self, mock_verify_token):
        """A logged-in user can connect Apple even with a hidden Apple email."""
        user = User.objects.create_user(
            email="real-email@example.com",
            username="realuser",
        )
        self.client.force_authenticate(user=user)
        mock_verify_token.return_value = {
            "sub": "apple-linked-user",
            "aud": "com.morelsoft.drawtwo.dev",
            "email": "private-relay@privaterelay.appleid.com",
            "email_verified": "true",
        }

        response = self.client.post(
            self.apple_link_url,
            {"identity_token": "valid-apple-identity-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "real-email@example.com")
        self.assertTrue(response.data["user"]["apple_connected"])

        social_account = SocialAccount.objects.get(provider="apple")
        self.assertEqual(social_account.uid, "apple-linked-user")
        self.assertEqual(social_account.user, user)

    @override_settings(
        APPLE_SIGN_IN_WEB_CLIENT_ID="com.morelsoft.drawtwo.dev.web",
        APPLE_SIGN_IN_IOS_CLIENT_ID="com.morelsoft.drawtwo.dev",
    )
    @patch("apps.authentication.views.verify_apple_identity_token")
    def test_apple_link_is_idempotent_for_existing_link(self, mock_verify_token):
        """Linking the same Apple account to the same user is a no-op success."""
        user = User.objects.create_user(email="linked-real@example.com")
        SocialAccount.objects.create(
            user=user,
            provider="apple",
            uid="apple-existing-link",
        )
        self.client.force_authenticate(user=user)
        mock_verify_token.return_value = {
            "sub": "apple-existing-link",
            "aud": "com.morelsoft.drawtwo.dev",
        }

        response = self.client.post(
            self.apple_link_url,
            {"identity_token": "valid-apple-identity-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(SocialAccount.objects.filter(provider="apple").count(), 1)
        self.assertTrue(response.data["user"]["apple_connected"])

    @override_settings(
        APPLE_SIGN_IN_WEB_CLIENT_ID="com.morelsoft.drawtwo.dev.web",
        APPLE_SIGN_IN_IOS_CLIENT_ID="com.morelsoft.drawtwo.dev",
    )
    @patch("apps.authentication.views.verify_apple_identity_token")
    def test_apple_link_rejects_apple_account_used_by_other_user(
        self, mock_verify_token
    ):
        """An Apple credential cannot silently merge into a second account."""
        intended_user = User.objects.create_user(email="intended@example.com")
        duplicate_user = User.objects.create_user(email="relay@example.com")
        SocialAccount.objects.create(
            user=duplicate_user,
            provider="apple",
            uid="apple-duplicate-link",
        )
        self.client.force_authenticate(user=intended_user)
        mock_verify_token.return_value = {
            "sub": "apple-duplicate-link",
            "aud": "com.morelsoft.drawtwo.dev",
        }

        response = self.client.post(
            self.apple_link_url,
            {"identity_token": "valid-apple-identity-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(response.data["apple_account_conflict"])
        self.assertFalse(
            SocialAccount.objects.filter(
                user=intended_user,
                provider="apple",
            ).exists()
        )

    def test_apple_link_requires_authentication(self):
        """Apple linking is only available from an existing Draw Two session."""
        response = self.client.post(
            self.apple_link_url,
            {"identity_token": "valid-apple-identity-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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
        self.account_delete_url = reverse("authentication:account_delete")

    def test_get_user_profile_authenticated(self):
        """Test getting user profile when authenticated."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "profile@example.com")
        self.assertEqual(response.data["username"], "profileuser")
        self.assertEqual(response.data["display_name"], "profileuser")
        self.assertFalse(response.data["apple_connected"])
        self.assertFalse(response.data["google_connected"])

    def test_get_user_profile_reports_connected_apple_account(self):
        """Profile includes whether Apple sign-in is connected."""
        SocialAccount.objects.create(
            user=self.user,
            provider="apple",
            uid="apple-profile-link",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["apple_connected"])

    def test_get_user_profile_reports_connected_google_account(self):
        """Profile includes whether Google sign-in is connected."""
        SocialAccount.objects.create(
            user=self.user,
            provider="google",
            uid="google-profile-link",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["google_connected"])

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

    def test_disconnect_google_account(self):
        """A user can disconnect a linked Google account."""
        SocialAccount.objects.create(
            user=self.user,
            provider="google",
            uid="google-disconnect",
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse("authentication:social_disconnect", args=["google"])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            SocialAccount.objects.filter(user=self.user, provider="google").exists()
        )
        self.assertFalse(response.data["user"]["google_connected"])

    @patch("apps.authentication.views.revoke_apple_token")
    def test_disconnect_apple_account_revokes_stored_token(self, mock_revoke):
        """Disconnecting Apple revokes its stored refresh token when available."""
        SocialAccount.objects.create(
            user=self.user,
            provider="apple",
            uid="apple-disconnect",
            extra_data={
                "apple_client_id": "com.morelsoft.drawtwo.dev",
                "apple_refresh_token": "apple-refresh-token",
            },
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse("authentication:social_disconnect", args=["apple"])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_revoke.assert_called_once_with(
            client_id="com.morelsoft.drawtwo.dev",
            token="apple-refresh-token",
            token_type_hint="refresh_token",
        )
        self.assertFalse(
            SocialAccount.objects.filter(user=self.user, provider="apple").exists()
        )

    def test_disconnect_missing_social_account_returns_error(self):
        """Disconnect requires the provider to be linked first."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse("authentication:social_disconnect", args=["google"])
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_account_delete_anonymizes_user_and_removes_auth_links(self):
        """Account deletion removes login links while preserving the user row."""
        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            primary=True,
            verified=True,
        )
        SocialAccount.objects.create(
            user=self.user,
            provider="google",
            uid="google-delete",
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.account_delete_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.deleted_at)
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.can_login())
        self.assertEqual(
            self.user.email,
            f"deleted-user-{self.user.id}@deleted.drawtwo.local",
        )
        self.assertIsNone(self.user.username)
        self.assertFalse(EmailAddress.objects.filter(user=self.user).exists())
        self.assertFalse(SocialAccount.objects.filter(user=self.user).exists())

    @patch("apps.authentication.views.revoke_apple_token")
    def test_account_delete_revokes_apple_refresh_token(self, mock_revoke):
        """Account deletion revokes linked Apple tokens before anonymizing the user."""
        SocialAccount.objects.create(
            user=self.user,
            provider="apple",
            uid="apple-delete",
            extra_data={
                "apple_client_id": "com.morelsoft.drawtwo.dev",
                "apple_refresh_token": "apple-refresh-token",
            },
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.account_delete_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_revoke.assert_called_once_with(
            client_id="com.morelsoft.drawtwo.dev",
            token="apple-refresh-token",
            token_type_hint="refresh_token",
        )


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
        self.assertEqual(minimal_user.display_name, f"Gamer {minimal_user.id}")

        self.assertEqual(full_user.username, "fulluser")
        self.assertEqual(full_user.display_name, "fulluser")

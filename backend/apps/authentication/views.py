import logging

from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import models, transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import permissions, status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .apple import (
    configured_apple_client_ids,
    exchange_apple_authorization_code,
    revoke_apple_token,
    verify_apple_identity_token,
)
from .serializers import (
    AppleLoginSerializer,
    EmailVerificationSerializer,
    FriendRequestSerializer,
    FriendshipSerializer,
    GoogleNativeLoginSerializer,
    LeaderboardUserSerializer,
    PasswordlessLoginSerializer,
    UserSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


def _login_url(base_url, key):
    """Append the one-time key to a configured login URL base."""
    return f"{base_url.rstrip('/')}/{key}"


def _frontend_email_confirm_url(key):
    base_url = getattr(settings, "FRONTEND_EMAIL_CONFIRM_URL", None)
    if not base_url:
        base_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth/email-confirm"
    return _login_url(base_url, key)


def _ios_universal_login_url(key):
    base_url = getattr(settings, "IOS_APP_LOGIN_URL", None)
    if not base_url:
        base_url = f"{settings.FRONTEND_URL.rstrip('/')}/app/login"
    return _login_url(base_url, key)


def _ios_scheme_login_url(key):
    return _login_url(settings.IOS_LOGIN_URL_SCHEME, key)


def _passwordless_login_message(client, key):
    if client == "ios":
        universal_url = _ios_universal_login_url(key)
        scheme_url = _ios_scheme_login_url(key)

        return (
            "Open this link on your iPhone to log in to DrawTwo:\n\n"
            f"{universal_url}\n\n"
            "If that opens in the browser instead, use this app link:\n\n"
            f"{scheme_url}\n\n"
            "You can also paste this confirmation code into the app:\n\n"
            f"{key}"
        )

    frontend_url = _frontend_email_confirm_url(key)
    return f"Click this link to log in: {frontend_url}"


@method_decorator(csrf_exempt, name="dispatch")
class GoogleLogin(SocialLoginView):
    """Google OAuth2 login view."""

    adapter_class = GoogleOAuth2Adapter
    callback_url = (
        settings.FRONTEND_URL + "/auth/callback/google"
    )  # Configurable frontend callback URL
    client_class = OAuth2Client
    # Disable DRF's SessionAuthentication which enforces CSRF independently.
    # This is necessary for iOS Safari where ITP may block the CSRF cookie.
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        """Override post to handle errors and mark email as verified after Google OAuth login."""
        try:
            response = super().post(request, *args, **kwargs)
        except PermissionDenied as e:
            # Handle signup disabled error from signal
            # DRF's PermissionDenied has a detail attribute
            error_message = getattr(e, "detail", str(e))
            if isinstance(error_message, list):
                error_message = error_message[0] if error_message else str(e)
            return Response(
                {
                    "error": error_message,
                    "signup_disabled": True,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # If login was successful, mark email as verified
        # Google has already verified the email, so we should trust it
        if response.status_code == status.HTTP_200_OK:
            user = None

            # Try to get user from response data first
            if hasattr(response, "data") and isinstance(response.data, dict):
                user_data = response.data.get("user")
                if user_data and isinstance(user_data, dict):
                    user_id = user_data.get("id")
                    if user_id:
                        try:
                            user = User.objects.get(id=user_id)
                        except User.DoesNotExist:
                            pass

            # Fallback: try to get user from authenticated request
            if not user and hasattr(request, "user") and request.user.is_authenticated:
                user = request.user

            # Mark email as verified if we found the user
            if user and not user.is_email_verified:
                user.is_email_verified = True
                user.save(update_fields=["is_email_verified"])

                # Also update the response data if it contains user info
                if hasattr(response, "data") and isinstance(response.data, dict):
                    user_data = response.data.get("user")
                    if user_data and isinstance(user_data, dict):
                        user_data["is_email_verified"] = True

        return response


@method_decorator(csrf_exempt, name="dispatch")
class GoogleNativeLoginView(APIView):
    """Exchange a native Google Sign-In ID token for DrawTwo JWTs."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = GoogleNativeLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        audience = settings.GOOGLE_OAUTH2_CLIENT_ID
        if not audience:
            return Response(
                {"error": "Google login is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            token_info = google_id_token.verify_oauth2_token(
                serializer.validated_data["id_token"],
                google_requests.Request(),
                audience,
            )
        except ValueError:
            return Response(
                {"error": "Invalid Google login token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = token_info.get("email")
        google_sub = token_info.get("sub")
        email_verified = token_info.get("email_verified")
        if not email or email_verified is not True:
            return Response(
                {"error": "Google did not return a verified email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.control.models import SiteSettings

        site_settings = SiteSettings.get_cached_settings()
        social_account = None
        if google_sub:
            social_account = (
                SocialAccount.objects.filter(provider="google", uid=google_sub)
                .select_related("user")
                .first()
            )

        user = social_account.user if social_account else None
        if not user:
            user = User.objects.filter(email__iexact=email).first()

        if not user:
            if site_settings.signup_disabled:
                return Response(
                    {
                        "error": (
                            "User registration is currently disabled. "
                            "Please contact an administrator."
                        ),
                        "signup_disabled": True,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            user = User.objects.create_user(
                email=email,
                avatar=token_info.get("picture") or None,
            )
        elif token_info.get("picture") and user.avatar != token_info["picture"]:
            user.avatar = token_info["picture"]

        if not user.is_email_verified:
            user.is_email_verified = True

        update_fields = ["is_email_verified"]
        if token_info.get("picture"):
            update_fields.append("avatar")
        user.save(update_fields=list(dict.fromkeys(update_fields)))

        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={"verified": True, "primary": True},
        )
        if google_sub:
            SocialAccount.objects.update_or_create(
                provider="google",
                uid=google_sub,
                defaults={
                    "user": user,
                    "extra_data": _google_extra_data(token_info),
                },
            )

        if site_settings.whitelist_mode_enabled and not user.can_login():
            return Response(
                {
                    "message": (
                        "Google login succeeded, but your account is pending "
                        "approval."
                    ),
                    "user": UserSerializer(user).data,
                    "requires_approval": True,
                },
                status=status.HTTP_200_OK,
            )

        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Google login successful.",
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name="dispatch")
class AppleLoginView(APIView):
    """Exchange a Sign in with Apple identity token for DrawTwo JWTs."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = AppleLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if not configured_apple_client_ids():
            return Response(
                {"error": "Apple login is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            token_info = verify_apple_identity_token(
                serializer.validated_data["identity_token"]
            )
        except ValueError:
            return Response(
                {"error": "Invalid Apple login token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        apple_sub = token_info.get("sub")
        if not apple_sub:
            return Response(
                {"error": "Apple did not return a user identifier."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = token_info.get("email")
        email_verified = _apple_email_verified(token_info.get("email_verified"))
        if email and not email_verified:
            return Response(
                {"error": "Apple did not return a verified email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.control.models import SiteSettings

        site_settings = SiteSettings.get_cached_settings()
        social_account = (
            SocialAccount.objects.filter(
                provider="apple",
                uid=apple_sub,
            )
            .select_related("user")
            .first()
        )

        user = social_account.user if social_account else None
        if not user and email:
            user = User.objects.filter(email__iexact=email).first()

        if not user:
            if not email:
                return Response(
                    {
                        "error": (
                            "Apple did not return an email address for this "
                            "unlinked account."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if site_settings.signup_disabled:
                return Response(
                    {
                        "error": (
                            "User registration is currently disabled. "
                            "Please contact an administrator."
                        ),
                        "signup_disabled": True,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            user = User.objects.create_user(email=email)

        if not social_account:
            social_account, _ = SocialAccount.objects.update_or_create(
                provider="apple",
                uid=apple_sub,
                defaults={
                    "user": user,
                    "extra_data": _apple_extra_data(token_info),
                },
            )
        else:
            _update_social_account_extra_data(
                social_account,
                _apple_extra_data(token_info),
            )

        _try_store_apple_refresh_token(
            social_account=social_account,
            token_info=token_info,
            authorization_code=serializer.validated_data.get("authorization_code"),
            redirect_uri=serializer.validated_data.get("redirect_uri"),
        )

        update_fields = []
        if (
            email
            and email_verified
            and email.casefold() == user.email.casefold()
            and not user.is_email_verified
        ):
            user.is_email_verified = True
            update_fields.append("is_email_verified")

        if update_fields:
            user.save(update_fields=update_fields)

        if email and email_verified and email.casefold() == user.email.casefold():
            EmailAddress.objects.update_or_create(
                user=user,
                email=user.email,
                defaults={"verified": True, "primary": True},
            )

        if site_settings.whitelist_mode_enabled and not user.can_login():
            return Response(
                {
                    "message": (
                        "Apple login succeeded, but your account is pending "
                        "approval."
                    ),
                    "user": UserSerializer(user).data,
                    "requires_approval": True,
                },
                status=status.HTTP_200_OK,
            )

        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Apple login successful.",
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name="dispatch")
class AppleLinkView(APIView):
    """Link Sign in with Apple to the currently authenticated DrawTwo account."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AppleLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if not configured_apple_client_ids():
            return Response(
                {"error": "Apple login is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            token_info = verify_apple_identity_token(
                serializer.validated_data["identity_token"]
            )
        except ValueError:
            return Response(
                {"error": "Invalid Apple login token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        apple_sub = token_info.get("sub")
        if not apple_sub:
            return Response(
                {"error": "Apple did not return a user identifier."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        linked_account = (
            SocialAccount.objects.filter(provider="apple", uid=apple_sub)
            .select_related("user")
            .first()
        )

        if linked_account:
            if linked_account.user_id != request.user.id:
                return Response(
                    {
                        "error": (
                            "This Apple account is already linked to another "
                            "Draw Two account."
                        ),
                        "apple_account_conflict": True,
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            _update_social_account_extra_data(
                linked_account,
                _apple_extra_data(token_info),
            )
            _try_store_apple_refresh_token(
                social_account=linked_account,
                token_info=token_info,
                authorization_code=serializer.validated_data.get("authorization_code"),
                redirect_uri=serializer.validated_data.get("redirect_uri"),
            )
            return Response(
                {
                    "message": "Apple sign-in is already connected.",
                    "user": UserSerializer(request.user).data,
                },
                status=status.HTTP_200_OK,
            )

        existing_account = SocialAccount.objects.filter(
            provider="apple",
            user=request.user,
        ).first()
        if existing_account:
            return Response(
                {
                    "error": (
                        "This Draw Two account is already linked to a different "
                        "Apple account."
                    ),
                    "apple_account_conflict": True,
                },
                status=status.HTTP_409_CONFLICT,
            )

        social_account = SocialAccount.objects.create(
            user=request.user,
            provider="apple",
            uid=apple_sub,
            extra_data=_apple_extra_data(token_info),
        )
        _try_store_apple_refresh_token(
            social_account=social_account,
            token_info=token_info,
            authorization_code=serializer.validated_data.get("authorization_code"),
            redirect_uri=serializer.validated_data.get("redirect_uri"),
        )

        return Response(
            {
                "message": "Apple sign-in connected.",
                "user": UserSerializer(request.user).data,
            },
            status=status.HTTP_200_OK,
        )


def _apple_extra_data(token_info):
    return {
        key: value for key, value in token_info.items() if key not in {"sub", "email"}
    }


def _google_extra_data(token_info):
    return {key: value for key, value in token_info.items() if key != "sub"}


def _update_social_account_extra_data(social_account, updates):
    extra_data = dict(social_account.extra_data or {})
    extra_data.update(updates)
    social_account.extra_data = extra_data
    social_account.save(update_fields=["extra_data"])


def _try_store_apple_refresh_token(
    social_account,
    token_info,
    authorization_code,
    redirect_uri=None,
):
    if not authorization_code:
        return

    client_id = token_info.get("aud")
    if not client_id:
        return

    try:
        token_response = exchange_apple_authorization_code(
            client_id=client_id,
            authorization_code=authorization_code,
            redirect_uri=redirect_uri,
        )
    except ValueError:
        logger.warning("Could not exchange Apple authorization code.", exc_info=True)
        return

    refresh_token = token_response.get("refresh_token")
    if not refresh_token:
        return

    extra_data = dict(social_account.extra_data or {})
    extra_data["apple_client_id"] = client_id
    extra_data["apple_refresh_token"] = refresh_token
    social_account.extra_data = extra_data
    social_account.save(update_fields=["extra_data"])


def _revoke_apple_social_account(social_account):
    extra_data = social_account.extra_data or {}
    refresh_token = extra_data.get("apple_refresh_token")
    client_id = extra_data.get("apple_client_id") or extra_data.get("aud")
    if not refresh_token or not client_id:
        return

    revoke_apple_token(
        client_id=client_id,
        token=refresh_token,
        token_type_hint="refresh_token",
    )


def _blacklist_user_refresh_tokens(user):
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )
    except ImportError:
        return

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


def _delete_account_related_data(user):
    EmailConfirmation.objects.filter(email_address__user=user).delete()
    EmailAddress.objects.filter(user=user).delete()
    SocialAccount.objects.filter(user=user).delete()

    from .models import Friendship

    Friendship.objects.filter(
        models.Q(user=user) | models.Q(friend=user) | models.Q(initiated_by=user)
    ).delete()

    try:
        from apps.gameplay.models import (
            FriendlyChallenge,
            MatchmakingQueue,
            PlayerNotification,
            PushDevice,
            PushNotificationEvent,
        )
    except ImportError:
        return

    MatchmakingQueue.objects.filter(user=user).delete()
    FriendlyChallenge.objects.filter(
        models.Q(challenger=user) | models.Q(challengee=user)
    ).delete()
    PlayerNotification.objects.filter(user=user).delete()
    PushDevice.objects.filter(user=user).delete()
    PushNotificationEvent.objects.filter(user=user).delete()


def _apple_email_verified(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.lower() == "true"

    return False


@method_decorator(csrf_exempt, name="dispatch")
class PasswordlessLoginView(APIView):
    """Send passwordless login email to user."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordlessLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            client = serializer.validated_data.get("client", "web")
            try:
                user = User.objects.get(email=email)

                # Create email confirmation manually
                email_address, created = EmailAddress.objects.get_or_create(
                    user=user,
                    email=user.email,
                    defaults={"verified": False, "primary": True},
                )

                # For passwordless login, we need to reset verification status
                # so the confirmation can work properly
                if not created and email_address.verified:
                    email_address.verified = False
                    email_address.save()

                # Create confirmation object
                confirmation = EmailConfirmation.create(email_address)
                confirmation.sent = timezone.now()
                confirmation.save()

                # Send email with console backend for development
                send_mail(
                    subject="DrawTwo - Login Link",
                    message=_passwordless_login_message(client, confirmation.key),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )

                return Response(
                    {
                        "message": "Login link sent to your email address.",
                        "email": email,
                    },
                    status=status.HTTP_200_OK,
                )

            except User.DoesNotExist:
                # Don't reveal if email doesn't exist for security
                return Response(
                    {
                        "message": (
                            "If an account with this email exists, "
                            "a login link has been sent."
                        ),
                        "email": email,
                    },
                    status=status.HTTP_200_OK,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name="dispatch")
class EmailConfirmationView(APIView):
    """Confirm email and log user in."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            key = serializer.validated_data["key"]

            try:
                confirmation = EmailConfirmation.objects.get(key=key)
                if confirmation.confirm(request):
                    user = confirmation.email_address.user

                    # Mark email as verified
                    user.is_email_verified = True
                    user.save()

                    # Check if user can login (considering whitelist mode)
                    from apps.control.models import SiteSettings

                    site_settings = SiteSettings.get_cached_settings()

                    if site_settings.whitelist_mode_enabled and not user.can_login():
                        return Response(
                            {
                                "message": "Email confirmed successfully, but your account is pending approval.",
                                "user": UserSerializer(user).data,
                                "requires_approval": True,
                            },
                            status=status.HTTP_200_OK,
                        )

                    # Generate JWT tokens only if user can login
                    from rest_framework_simplejwt.tokens import RefreshToken

                    refresh = RefreshToken.for_user(user)

                    return Response(
                        {
                            "message": "Email confirmed successfully.",
                            "user": UserSerializer(user).data,
                            "access": str(refresh.access_token),
                            "refresh": str(refresh),
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"error": "Invalid or expired confirmation link."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            except EmailConfirmation.DoesNotExist:
                return Response(
                    {"error": "Invalid confirmation link."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """Get and update user profile."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get current user profile."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        """Update user profile."""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SocialDisconnectView(APIView):
    """Disconnect a social sign-in provider from the current account."""

    permission_classes = [permissions.IsAuthenticated]
    allowed_providers = {"apple", "google"}

    def delete(self, request, provider):
        provider = provider.lower()
        if provider not in self.allowed_providers:
            return Response(
                {"error": "Unsupported sign-in provider."},
                status=status.HTTP_404_NOT_FOUND,
            )

        social_account = SocialAccount.objects.filter(
            user=request.user,
            provider=provider,
        ).first()
        if not social_account:
            return Response(
                {"error": f"{provider.title()} sign-in is not connected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if provider == "apple":
            try:
                _revoke_apple_social_account(social_account)
            except ValueError:
                logger.warning("Could not revoke Apple token.", exc_info=True)
                return Response(
                    {"error": "Could not disconnect Apple sign-in. Please try again."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        social_account.delete()
        return Response(
            {
                "message": f"{provider.title()} sign-in disconnected.",
                "user": UserSerializer(request.user).data,
            },
            status=status.HTTP_200_OK,
        )


class AccountDeletionView(APIView):
    """Delete the current user's account while preserving non-personal game history."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        social_accounts = list(SocialAccount.objects.filter(user=user))
        for social_account in social_accounts:
            if social_account.provider != "apple":
                continue

            try:
                _revoke_apple_social_account(social_account)
            except ValueError:
                logger.warning(
                    "Could not revoke Apple token during account deletion.",
                    exc_info=True,
                )
                return Response(
                    {"error": "Could not delete account. Please try again."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        with transaction.atomic():
            _blacklist_user_refresh_tokens(user)
            _delete_account_related_data(user)
            user.anonymize_for_deletion()

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def protected_test_view(request):
    """Test view to verify authentication is working."""
    return Response(
        {
            "message": "Authentication is working!",
            "user": {
                "id": request.user.id,
                "email": request.user.email,
                "display_name": request.user.display_name,
            },
        }
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
@csrf_exempt
def register_view(request):
    """Register a new user and send email verification."""
    from apps.control.models import SiteSettings

    from .serializers import CustomRegisterSerializer

    # Check if signup is disabled
    site_settings = SiteSettings.get_cached_settings()
    if site_settings.signup_disabled:
        return Response(
            {
                "error": "User registration is currently disabled. Please contact an administrator.",
                "signup_disabled": True,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = CustomRegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save(request)

        # New users start as pending by default (already set in model)
        message = (
            "Registration successful. Please check your email to "
            "verify your account."
        )

        # Add additional message if whitelist mode is enabled
        if site_settings.whitelist_mode_enabled:
            message += (
                " Your account will need to be approved by an administrator "
                "before you can access the site."
            )

        return Response(
            {
                "message": message,
                "user": UserSerializer(user).data,
                "requires_approval": site_settings.whitelist_mode_enabled,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FriendshipListView(APIView):
    """List all friends and pending requests."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get all friendships for the current user."""
        from .models import Friendship

        # Get all friendships where user is involved
        friendships = Friendship.objects.filter(user=request.user).select_related(
            "friend"
        )

        serializer = FriendshipSerializer(
            friendships, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request):
        """Create a new friend request."""
        from django.db import transaction

        from .models import Friendship

        serializer = FriendRequestSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            username = serializer.validated_data["username"]
            target_user = User.objects.get(username__iexact=username)

            # Create bidirectional friendship records
            with transaction.atomic():
                # Record from requester's perspective (pending)
                friendship1 = Friendship.objects.create(
                    user=request.user,
                    friend=target_user,
                    status=Friendship.STATUS_PENDING,
                    initiated_by=request.user,
                )

                # Record from target's perspective (also pending, waiting for acceptance)
                friendship2 = Friendship.objects.create(
                    user=target_user,
                    friend=request.user,
                    status=Friendship.STATUS_PENDING,
                    initiated_by=request.user,
                )

            return Response(
                FriendshipSerializer(friendship1, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FriendshipDetailView(APIView):
    """Manage individual friendship."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        """Accept or decline a friend request."""
        from django.db import transaction

        from .models import Friendship

        try:
            # Get the friendship where the current user is the recipient
            friendship = Friendship.objects.get(pk=pk, user=request.user)
            # Check that the current user didn't initiate it
            if friendship.initiated_by == request.user:
                return Response(
                    {"error": "Cannot accept your own friend request."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Friendship.DoesNotExist:
            return Response(
                {"error": "Friendship not found or you are not authorized."},
                status=status.HTTP_404_NOT_FOUND,
            )

        action = request.data.get("action")

        if action == "accept":
            # Update both sides of the friendship
            with transaction.atomic():
                Friendship.objects.filter(
                    user=request.user, friend=friendship.friend
                ).update(status=Friendship.STATUS_ACCEPTED)
                Friendship.objects.filter(
                    user=friendship.friend, friend=request.user
                ).update(status=Friendship.STATUS_ACCEPTED)

            friendship.refresh_from_db()
            return Response(
                FriendshipSerializer(friendship, context={"request": request}).data
            )

        elif action == "decline":
            # Delete both sides of the friendship
            with transaction.atomic():
                Friendship.objects.filter(
                    user=request.user, friend=friendship.friend
                ).delete()
                Friendship.objects.filter(
                    user=friendship.friend, friend=request.user
                ).delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {"error": "Invalid action. Use 'accept' or 'decline'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, pk):
        """Remove a friend."""
        from django.db import transaction

        from .models import Friendship

        try:
            friendship = Friendship.objects.get(pk=pk, user=request.user)
        except Friendship.DoesNotExist:
            return Response(
                {"error": "Friendship not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Delete both sides of the friendship
        with transaction.atomic():
            Friendship.objects.filter(
                user=request.user, friend=friendship.friend
            ).delete()
            Friendship.objects.filter(
                user=friendship.friend, friend=request.user
            ).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class LeaderboardView(APIView):
    """Get ELO rating leaderboard for a specific title."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, title_slug):
        """
        Get top players by ELO rating for a specific title.

        Args:
            title_slug: The slug of the title to get leaderboard for
        """
        from django.db.models import Count, F, Q

        from apps.builder.models import Title
        from apps.gameplay.models import Game, UserTitleRating

        # Get the title
        try:
            title = Title.objects.get(slug=title_slug)
        except Title.DoesNotExist:
            return Response(
                {"error": f'Title "{title_slug}" not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        ladder_type = request.query_params.get("ladder_type", Game.LADDER_TYPE_RAPID)
        if ladder_type not in dict(Game.LADDER_TYPE_CHOICES):
            return Response(
                {"error": "Invalid ladder type"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get limit from query params (default 100, max 1000)
        limit = min(int(request.query_params.get("limit", 100)), 1000)

        # Get all user ratings for this title, annotated with win/loss counts
        user_ratings = (
            UserTitleRating.objects.filter(
                title=title,
                ladder_type=ladder_type,
            )
            .select_related("user")
            .annotate(
                wins=Count(
                    "user__elo_wins",
                    filter=Q(
                        user__elo_wins__title=title,
                        user__elo_wins__ladder_type=ladder_type,
                    ),
                    distinct=True,
                ),
                losses=Count(
                    "user__elo_losses",
                    filter=Q(
                        user__elo_losses__title=title,
                        user__elo_losses__ladder_type=ladder_type,
                    ),
                    distinct=True,
                ),
            )
            .annotate(total_games=F("wins") + F("losses"))
            .filter(
                # Only include users who have played at least 5 games
                total_games__gte=5
            )
            .order_by("-elo_rating")[:limit]
        )

        # Build response data
        leaderboard_data = []
        for rating in user_ratings:
            wins = rating.wins
            losses = rating.losses
            total_games = wins + losses

            leaderboard_data.append(
                {
                    "id": rating.user.id,
                    "username": rating.user.username,
                    "display_name": rating.user.display_name,
                    "avatar": rating.user.avatar,
                    "elo_rating": rating.elo_rating,
                    "wins": wins,
                    "losses": losses,
                    "total_games": total_games,
                }
            )

        return Response(leaderboard_data)


class UserTitleRatingView(APIView):
    """Get current user's rating for a specific title."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, title_slug):
        """Get the authenticated user's rating for a specific title."""
        from django.db.models import Count, Q

        from apps.builder.models import Title
        from apps.gameplay.models import Game, UserTitleRating

        try:
            title = Title.objects.get(slug=title_slug)
        except Title.DoesNotExist:
            return Response(
                {"error": f'Title "{title_slug}" not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        ladder_type = request.query_params.get("ladder_type", Game.LADDER_TYPE_RAPID)
        if ladder_type not in dict(Game.LADDER_TYPE_CHOICES):
            return Response(
                {"error": "Invalid ladder type"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get or create the user's rating for this title
            user_rating = (
                UserTitleRating.objects.select_related("user")
                .annotate(
                    wins=Count(
                        "user__elo_wins",
                        filter=Q(
                            user__elo_wins__title=title,
                            user__elo_wins__ladder_type=ladder_type,
                        ),
                        distinct=True,
                    ),
                    losses=Count(
                        "user__elo_losses",
                        filter=Q(
                            user__elo_losses__title=title,
                            user__elo_losses__ladder_type=ladder_type,
                        ),
                        distinct=True,
                    ),
                )
                .get(user=request.user, title=title, ladder_type=ladder_type)
            )

            wins = user_rating.wins
            losses = user_rating.losses

            return Response(
                {
                    "id": request.user.id,
                    "username": request.user.username,
                    "display_name": request.user.display_name,
                    "avatar": request.user.avatar,
                    "elo_rating": user_rating.elo_rating,
                    "ladder_type": ladder_type,
                    "wins": wins,
                    "losses": losses,
                    "total_games": wins + losses,
                }
            )
        except UserTitleRating.DoesNotExist:
            # User hasn't played any games for this title yet
            return Response(
                {
                    "id": request.user.id,
                    "username": request.user.username,
                    "display_name": request.user.display_name,
                    "avatar": request.user.avatar,
                    "elo_rating": 1200,  # Default rating
                    "ladder_type": ladder_type,
                    "wins": 0,
                    "losses": 0,
                    "total_games": 0,
                }
            )

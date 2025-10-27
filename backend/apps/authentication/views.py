from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    EmailVerificationSerializer,
    PasswordlessLoginSerializer,
    UserSerializer,
    FriendshipSerializer,
    FriendRequestSerializer,
)

User = get_user_model()


@method_decorator(csrf_exempt, name="dispatch")
class GoogleLogin(SocialLoginView):
    """Google OAuth2 login view."""

    adapter_class = GoogleOAuth2Adapter
    callback_url = (
        settings.FRONTEND_URL + "/auth/callback/google"
    )  # Configurable frontend callback URL
    client_class = OAuth2Client


@method_decorator(csrf_exempt, name="dispatch")
class PasswordlessLoginView(APIView):
    """Send passwordless login email to user."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordlessLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
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

                # Create custom login link for frontend
                frontend_url = (
                    f"{settings.FRONTEND_EMAIL_CONFIRM_URL}/" f"{confirmation.key}"
                )

                # Send email with console backend for development
                send_mail(
                    subject="DrawTwo - Login Link",
                    message=f"Click this link to log in: {frontend_url}",
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
@csrf_exempt
def register_view(request):
    """Register a new user and send email verification."""
    from .serializers import CustomRegisterSerializer
    from apps.control.models import SiteSettings

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
        from .models import Friendship
        from django.db import transaction

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
        from .models import Friendship
        from django.db import transaction

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
        from .models import Friendship
        from django.db import transaction

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

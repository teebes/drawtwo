from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    EmailVerificationSerializer,
    PasswordlessLoginSerializer,
    UserSerializer,
    FriendshipSerializer,
    FriendRequestSerializer,
    LeaderboardUserSerializer,
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
            error_message = getattr(e, 'detail', str(e))
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
            if hasattr(response, 'data') and isinstance(response.data, dict):
                user_data = response.data.get('user')
                if user_data and isinstance(user_data, dict):
                    user_id = user_data.get('id')
                    if user_id:
                        try:
                            user = User.objects.get(id=user_id)
                        except User.DoesNotExist:
                            pass

            # Fallback: try to get user from authenticated request
            if not user and hasattr(request, 'user') and request.user.is_authenticated:
                user = request.user

            # Mark email as verified if we found the user
            if user and not user.is_email_verified:
                user.is_email_verified = True
                user.save(update_fields=['is_email_verified'])

                # Also update the response data if it contains user info
                if hasattr(response, 'data') and isinstance(response.data, dict):
                    user_data = response.data.get('user')
                    if user_data and isinstance(user_data, dict):
                        user_data['is_email_verified'] = True

        return response


@method_decorator(csrf_exempt, name="dispatch")
class PasswordlessLoginView(APIView):
    """Send passwordless login email to user."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

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
        from apps.gameplay.models import UserTitleRating, Game

        # Get the title
        try:
            title = Title.objects.get(slug=title_slug)
        except Title.DoesNotExist:
            return Response(
                {'error': f'Title "{title_slug}" not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        ladder_type = request.query_params.get('ladder_type', Game.LADDER_TYPE_RAPID)
        if ladder_type not in dict(Game.LADDER_TYPE_CHOICES):
            return Response({'error': 'Invalid ladder type'}, status=status.HTTP_400_BAD_REQUEST)

        # Get limit from query params (default 100, max 1000)
        limit = min(int(request.query_params.get('limit', 100)), 1000)

        # Get all user ratings for this title, annotated with win/loss counts
        user_ratings = UserTitleRating.objects.filter(
            title=title,
            ladder_type=ladder_type,
        ).select_related('user').annotate(
            wins=Count(
                'user__elo_wins',
                filter=Q(user__elo_wins__title=title, user__elo_wins__ladder_type=ladder_type),
                distinct=True
            ),
            losses=Count(
                'user__elo_losses',
                filter=Q(user__elo_losses__title=title, user__elo_losses__ladder_type=ladder_type),
                distinct=True
            )
        ).annotate(
            total_games=F('wins') + F('losses')
        ).filter(
            # Only include users who have played at least 5 games
            total_games__gte=5
        ).order_by('-elo_rating')[:limit]

        # Build response data
        leaderboard_data = []
        for rating in user_ratings:
            wins = rating.wins
            losses = rating.losses
            total_games = wins + losses

            leaderboard_data.append({
                'id': rating.user.id,
                'username': rating.user.username,
                'display_name': rating.user.display_name,
                'avatar': rating.user.avatar,
                'elo_rating': rating.elo_rating,
                'wins': wins,
                'losses': losses,
                'total_games': total_games,
            })

        return Response(leaderboard_data)


class UserTitleRatingView(APIView):
    """Get current user's rating for a specific title."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, title_slug):
        """Get the authenticated user's rating for a specific title."""
        from apps.builder.models import Title
        from apps.gameplay.models import UserTitleRating, Game
        from django.db.models import Count, Q

        try:
            title = Title.objects.get(slug=title_slug)
        except Title.DoesNotExist:
            return Response(
                {'error': f'Title "{title_slug}" not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        ladder_type = request.query_params.get('ladder_type', Game.LADDER_TYPE_RAPID)
        if ladder_type not in dict(Game.LADDER_TYPE_CHOICES):
            return Response({'error': 'Invalid ladder type'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get or create the user's rating for this title
            user_rating = UserTitleRating.objects.select_related('user').annotate(
                wins=Count(
                    'user__elo_wins',
                    filter=Q(user__elo_wins__title=title, user__elo_wins__ladder_type=ladder_type),
                    distinct=True
                ),
                losses=Count(
                    'user__elo_losses',
                    filter=Q(user__elo_losses__title=title, user__elo_losses__ladder_type=ladder_type),
                    distinct=True
                )
            ).get(user=request.user, title=title, ladder_type=ladder_type)

            wins = user_rating.wins
            losses = user_rating.losses

            return Response({
                'id': request.user.id,
                'username': request.user.username,
                'display_name': request.user.display_name,
                'avatar': request.user.avatar,
                'elo_rating': user_rating.elo_rating,
                'ladder_type': ladder_type,
                'wins': wins,
                'losses': losses,
                'total_games': wins + losses,
            })
        except UserTitleRating.DoesNotExist:
            # User hasn't played any games for this title yet
            return Response({
                'id': request.user.id,
                'username': request.user.username,
                'display_name': request.user.display_name,
                'avatar': request.user.avatar,
                'elo_rating': 1200,  # Default rating
                'ladder_type': ladder_type,
                'wins': 0,
                'losses': 0,
                'total_games': 0,
            })

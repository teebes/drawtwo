from allauth.account import app_settings as allauth_settings
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from dj_rest_auth.registration.serializers import RegisterSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Friendship

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details."""

    display_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "display_name",
            "avatar",
            "is_email_verified",
            "is_staff",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "is_email_verified",
            "is_staff",
            "status",
        )


class CustomRegisterSerializer(RegisterSerializer):
    """Custom registration serializer for passwordless email signup."""

    # Remove inherited fields we don't want
    username = None
    password1 = None  # Remove password fields for passwordless
    password2 = None

    email = serializers.EmailField(required=True)
    username = serializers.CharField(
        max_length=150, required=False, allow_blank=True, allow_null=True
    )

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if allauth_settings.UNIQUE_EMAIL:
            if email and User.objects.filter(email__iexact=email).exists():
                raise serializers.ValidationError(
                    "A user is already registered with this e-mail address."
                )
        return email

    def validate_username(self, username):
        """Validate that username is unique if provided."""
        if username:
            if User.objects.filter(username__iexact=username).exists():
                raise serializers.ValidationError(
                    "A user with this username already exists."
                )
        return username

    def validate(self, data):
        # Skip password validation since we're passwordless
        return data

    def get_cleaned_data(self):
        return {
            "email": self.validated_data.get("email", ""),
            "username": self.validated_data.get("username", "") or None,
        }

    def save(self, request):
        """Override save to create user without password."""
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()

        user.email = self.cleaned_data.get("email")
        user.username = self.cleaned_data.get("username")

        # Don't set a password for passwordless users
        user.set_unusable_password()
        user.save()

        setup_user_email(request, user, [])
        return user


class PasswordlessLoginSerializer(serializers.Serializer):
    """Serializer for passwordless login via email."""

    email = serializers.EmailField(required=True)

    def validate_email(self, email):
        """Validate that the email exists in the system."""
        if not User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "No account found with this email address."
            )
        return email


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification."""

    key = serializers.CharField(required=True)


class SocialLoginSerializer(serializers.Serializer):
    """
    Serializer for social login tokens.
    """

    access_token = serializers.CharField(required=True)


class FriendUserSerializer(serializers.ModelSerializer):
    """Simplified user serializer for friend lists."""

    display_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ("id", "username", "display_name", "avatar")
        read_only_fields = fields


class LeaderboardUserSerializer(serializers.ModelSerializer):
    """Serializer for leaderboard entries."""

    display_name = serializers.ReadOnlyField()
    wins = serializers.IntegerField(read_only=True)
    losses = serializers.IntegerField(read_only=True)
    total_games = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "display_name", "avatar", "elo_rating", "wins", "losses", "total_games")
        read_only_fields = fields


class FriendshipSerializer(serializers.ModelSerializer):
    """Serializer for friendship data."""

    friend_data = FriendUserSerializer(source="friend", read_only=True)
    is_initiator = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = (
            "id",
            "friend",
            "friend_data",
            "status",
            "is_initiator",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_is_initiator(self, obj):
        """Check if the current user initiated this friendship."""
        request = self.context.get("request")
        if request and request.user:
            return obj.initiated_by_id == request.user.id
        return False


class FriendRequestSerializer(serializers.Serializer):
    """Serializer for creating friend requests."""

    username = serializers.CharField(required=True)

    def validate_username(self, username):
        """Validate that the username exists and is not the current user."""
        request = self.context.get("request")

        # Check user exists
        if not User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("User not found.")

        target_user = User.objects.get(username__iexact=username)

        # Can't friend yourself
        if request and request.user.id == target_user.id:
            raise serializers.ValidationError(
                "You cannot send a friend request to yourself."
            )

        # Check if friendship already exists
        if Friendship.objects.filter(user=request.user, friend=target_user).exists():
            raise serializers.ValidationError("Friendship request already exists.")

        return username

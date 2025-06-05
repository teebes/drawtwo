from allauth.account import app_settings as allauth_settings
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from dj_rest_auth.registration.serializers import RegisterSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers

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
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "is_email_verified")


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

from allauth.account import app_settings as allauth_settings
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from dj_rest_auth.registration.serializers import RegisterSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details."""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "avatar",
            "is_email_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "is_email_verified")


class CustomRegisterSerializer(RegisterSerializer):
    """Custom registration serializer for passwordless email signup."""

    username = None  # Remove username field
    password1 = None  # Remove password fields for passwordless
    password2 = None

    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=30, required=False, allow_blank=True)

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if allauth_settings.UNIQUE_EMAIL:
            if email and User.objects.filter(email__iexact=email).exists():
                raise serializers.ValidationError(
                    "A user is already registered with this e-mail address."
                )
        return email

    def validate(self, data):
        # Skip password validation since we're passwordless
        return data

    def get_cleaned_data(self):
        return {
            "email": self.validated_data.get("email", ""),
            "first_name": self.validated_data.get("first_name", ""),
            "last_name": self.validated_data.get("last_name", ""),
        }

    def save(self, request):
        """Override save to create user without password."""
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()

        user.email = self.cleaned_data.get("email")
        user.first_name = self.cleaned_data.get("first_name")
        user.last_name = self.cleaned_data.get("last_name")

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

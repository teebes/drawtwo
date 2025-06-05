from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with email and password."""
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model that uses email instead of username for authentication.
    Extensible for future features like user profiles, preferences, etc.
    """

    email = models.EmailField(unique=True)

    # Optional username for multiplayer features
    username = models.CharField(
        max_length=150,
        unique=True,
        null=True,
        blank=True,
        help_text=(
            "Optional username for multiplayer features. " "Must be unique if provided."
        ),
    )

    # Remove first_name and last_name inherited from AbstractUser
    first_name = None
    last_name = None

    # User profile fields
    avatar = models.URLField(blank=True, null=True)  # For social auth profile pictures

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Authentication fields
    is_email_verified = models.BooleanField(default=False)

    objects = UserManager()  # Use our custom manager

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = (
        []
    )  # Remove email from required fields since it's the username field

    class Meta:
        db_table = "auth_user"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username or self.email

    @property
    def display_name(self):
        """Returns the user's display name."""
        return self.username or self.email

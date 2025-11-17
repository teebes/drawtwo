"""
Signal handlers for authentication app.
"""
from allauth.socialaccount.signals import social_account_added, pre_social_login
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from rest_framework.exceptions import PermissionDenied

User = get_user_model()


@receiver(pre_social_login)
def prevent_signup_when_disabled(sender, request, sociallogin, **kwargs):
    """
    Prevent new user signups via social auth when signups are disabled.

    This signal fires before the user is created, allowing us to block
    new signups while still allowing existing users to log in.
    """
    from apps.control.models import SiteSettings

    site_settings = SiteSettings.get_cached_settings()

    if site_settings.signup_disabled:
        # Check if this is a new user (user doesn't exist yet)
        # sociallogin.user will be a new unsaved user if it's a signup
        email = sociallogin.email
        if email:
            # Check if user with this email already exists
            user_exists = User.objects.filter(email__iexact=email).exists()

            # If user doesn't exist, this is a new signup - block it
            if not user_exists:
                raise PermissionDenied(
                    "User registration is currently disabled. Please contact an administrator."
                )


@receiver(social_account_added)
def mark_email_verified_on_social_login(sender, request, sociallogin, **kwargs):
    """
    Mark user's email as verified when they log in via a social provider.

    Social providers (like Google) have already verified the email address,
    so we should trust their verification and mark it as verified in our system.
    """
    user = sociallogin.user
    if user and not user.is_email_verified:
        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])

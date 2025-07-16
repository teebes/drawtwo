from django.db import models
from django.core.cache import cache


class SiteSettings(models.Model):
    """
    Site-wide settings for controlling access and features.
    Should only have one instance (singleton pattern).
    """

    # Site access controls
    whitelist_mode_enabled = models.BooleanField(
        default=False,
        help_text="When enabled, only approved users can log in and use the site"
    )

    signup_disabled = models.BooleanField(
        default=False,
        help_text="When enabled, new user registrations are completely disabled"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"

    @classmethod
    def get_settings(cls):
        """Get or create site settings (singleton pattern)."""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

    @classmethod
    def get_cached_settings(cls):
        """Get site settings with caching for performance."""
        cache_key = 'site_settings'
        settings = cache.get(cache_key)

        if settings is None:
            settings = cls.get_settings()
            cache.set(cache_key, settings, 60 * 15)  # Cache for 15 minutes

        return settings

    def save(self, *args, **kwargs):
        """Override save to clear cache and enforce singleton pattern."""
        self.pk = 1  # Force primary key to 1 for singleton
        super().save(*args, **kwargs)
        # Clear cache when settings are updated
        cache.delete('site_settings')

    def delete(self, *args, **kwargs):
        """Prevent deletion of settings."""
        pass  # Don't allow deletion of site settings

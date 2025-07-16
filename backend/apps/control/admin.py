from django.contrib import admin
from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin interface for site settings."""

    list_display = (
        'whitelist_mode_enabled',
        'signup_disabled',
        'updated_at',
    )

    fieldsets = (
        ('Site Access Controls', {
            'fields': (
                'whitelist_mode_enabled',
                'signup_disabled',
            ),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    def has_add_permission(self, request):
        """Only allow adding if no settings exist."""
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Don't allow deletion of site settings."""
        return False

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from .models import SiteSettings

User = get_user_model()


class SiteSettingsSerializer(serializers.ModelSerializer):
    """Serializer for site settings."""

    class Meta:
        model = SiteSettings
        fields = [
            'whitelist_mode_enabled',
            'signup_disabled',
            'updated_at'
        ]
        read_only_fields = ['updated_at']


class UserManagementSerializer(serializers.ModelSerializer):
    """Serializer for user management in the control panel."""

    display_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'display_name',
            'status',
            'is_email_verified',
            'is_staff',
            'is_active',
            'created_at',
            'updated_at',
            'last_login'
        ]
        read_only_fields = [
            'id',
            'email',
            'username',
            'display_name',
            'is_email_verified',
            'created_at',
            'updated_at',
            'last_login'
        ]


class UserStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating user status."""

    status = serializers.ChoiceField(choices=User.STATUS_CHOICES)

    def validate_status(self, value):
        """Validate the status value."""
        if value not in [choice[0] for choice in User.STATUS_CHOICES]:
            raise serializers.ValidationError("Invalid status value.")
        return value


class UserAnalyticsSerializer(serializers.Serializer):
    """Serializer for user analytics data."""

    total_users = serializers.IntegerField()
    users_last_week = serializers.IntegerField()
    pending_users = serializers.IntegerField()
    approved_users = serializers.IntegerField()
    suspended_users = serializers.IntegerField()
    banned_users = serializers.IntegerField()

    # Recent signup trend (last 7 days)
    recent_signups = serializers.ListField(
        child=serializers.DictField(),
        help_text="Daily signup counts for the last 7 days"
    )


class RecentUsersSerializer(serializers.ModelSerializer):
    """Serializer for recent user signups."""

    display_name = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'display_name',
            'status',
            'status_display',
            'is_email_verified',
            'created_at'
        ]
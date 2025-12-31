from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

from .models import SiteSettings
from apps.gameplay.models import MatchmakingQueue

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


class MatchmakingQueueEntrySerializer(serializers.ModelSerializer):
    """Serializer for matchmaking queue entries in the control panel."""

    user_display_name = serializers.CharField(source='user.display_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    deck_name = serializers.CharField(source='deck.name', read_only=True)
    deck_id = serializers.IntegerField(source='deck.id', read_only=True)
    hero_name = serializers.CharField(source='deck.hero.name', read_only=True)
    title_name = serializers.CharField(source='deck.title.name', read_only=True)
    title_slug = serializers.CharField(source='deck.title.slug', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    wait_seconds = serializers.SerializerMethodField()
    matched_with_entry = serializers.SerializerMethodField()
    ladder_type_display = serializers.CharField(source='get_ladder_type_display', read_only=True)

    class Meta:
        model = MatchmakingQueue
        fields = [
            'id',
            'status',
            'status_display',
            'ladder_type',
            'ladder_type_display',
            'elo_rating',
            'created_at',
            'updated_at',
            'user_id',
            'user_display_name',
            'user_email',
            'deck_id',
            'deck_name',
            'hero_name',
            'title_name',
            'title_slug',
            'game_id',
            'matched_with_entry',
            'wait_seconds',
        ]

    def get_wait_seconds(self, obj):
        delta = timezone.now() - obj.created_at
        return int(delta.total_seconds())

    def get_matched_with_entry(self, obj):
        if not obj.matched_with_id:
            return None
        partner = obj.matched_with
        return {
            'id': obj.matched_with_id,
            'user_display_name': getattr(getattr(partner, 'user', None), 'display_name', None),
            'status': getattr(partner, 'status', None),
        }

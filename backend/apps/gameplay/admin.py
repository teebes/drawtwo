from django.contrib import admin
from django.utils import timezone

from .models import (
    ELORatingChange,
    FriendlyChallenge,
    Game,
    GameUpdate,
    MatchmakingQueue,
    UserTitleRating,
)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['id', '__str__', 'status', 'get_game_type', 'ladder_type', 'get_winner', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = [
        'side_a__name',
        'side_b__name',
        'side_a__user__email',
        'side_b__user__email',
        'side_a__ai_player__name',
        'side_b__ai_player__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'is_vs_ai']

    fieldsets = (
        ('Game Setup', {
            'fields': ('type', 'ladder_type', 'status', 'side_a', 'side_b')
        }),
        ('Game State', {
            'fields': ('state',),
            'classes': ('collapse',)
        }),
        ('Game Queue', {
            'fields': ('queue',),
            'classes': ('collapse',)
        }),
        ('Results', {
            'fields': ('winner',)
        }),
        ('Info', {
            'fields': ('is_vs_ai', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_game_type(self, obj):
        if obj.is_vs_ai:
            return "🤖 vs Human"
        return "👤 vs Human"
    get_game_type.short_description = "Game Type"

    def get_winner(self, obj):
        if obj.winner:
            if obj.winner.is_ai_deck:
                return f"🤖 {obj.winner.name}"
            else:
                return f"👤 {obj.winner.name}"
        return "No winner yet"
    get_winner.short_description = "Winner"


@admin.register(GameUpdate)
class GameUpdateAdmin(admin.ModelAdmin):
    list_display = ['id', 'game', 'get_update_type', 'created_at']
    list_filter = ['created_at']
    search_fields = [
        'game__side_a__name',
        'game__side_b__name',
        'game__side_a__user__email',
        'game__side_b__user__email',
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['game']

    fieldsets = (
        ('Game', {
            'fields': ('game',)
        }),
        ('Update', {
            'fields': ('update',)
        }),
        ('Info', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_update_type(self, obj):
        try:
            return obj.update.get('type')
        except Exception:
            return None
    get_update_type.short_description = "Update Type"


@admin.register(UserTitleRating)
class UserTitleRatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'ladder_type', 'elo_rating', 'updated_at']
    list_filter = ['title', 'ladder_type', 'updated_at']
    search_fields = ['user__username', 'user__email', 'title__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['title', 'ladder_type', '-elo_rating']


@admin.register(ELORatingChange)
class ELORatingChangeAdmin(admin.ModelAdmin):
    list_display = [
        'game',
        'title',
        'ladder_type',
        'winner',
        'winner_rating_change',
        'loser',
        'loser_rating_change',
        'created_at',
    ]
    list_filter = ['title', 'ladder_type', 'created_at']
    search_fields = ['winner__username', 'winner__email', 'loser__username', 'loser__email']
    readonly_fields = [
        'game',
        'title',
        'winner',
        'winner_old_rating',
        'winner_new_rating',
        'winner_rating_change',
        'loser',
        'loser_old_rating',
        'loser_new_rating',
        'loser_rating_change',
        'created_at',
    ]


@admin.register(MatchmakingQueue)
class MatchmakingQueueAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'deck',
        'status',
        'ladder_type',
        'elo_rating',
        'matched_partner_display',
        'game',
        'queue_age',
        'created_at',
    ]
    list_filter = ['status', 'ladder_type', 'created_at', 'deck__title']
    search_fields = [
        'user__username',
        'user__email',
        'deck__name',
        'deck__title__name',
    ]
    readonly_fields = ['created_at', 'updated_at', 'queue_age', 'matched_partner_display']
    raw_id_fields = ['user', 'deck', 'matched_with', 'game']
    list_select_related = [
        'user',
        'deck',
        'deck__title',
        'matched_with',
        'matched_with__user',
        'game',
    ]
    ordering = ['-created_at']
    actions = ['mark_as_cancelled', 'reset_to_queued']
    list_per_page = 50

    fieldsets = (
        (None, {
            'fields': (
                'user',
                'deck',
                'ladder_type',
                'status',
                'elo_rating',
            )
        }),
        ('Matchmaking State', {
            'fields': (
                'matched_with',
                'matched_partner_display',
                'game',
            )
        }),
        ('Timestamps', {
            'fields': ('queue_age', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description="Matched Partner")
    def matched_partner_display(self, obj):
        if not obj.matched_with:
            return "-"
        partner_user = getattr(obj.matched_with, 'user', None)
        if partner_user:
            return partner_user.display_name or partner_user.email
        return f"Entry #{obj.matched_with_id}"

    @admin.display(description="Queue Age")
    def queue_age(self, obj):
        delta = timezone.now() - obj.created_at
        total_seconds = int(delta.total_seconds())
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    @admin.action(description="Mark selected entries as cancelled")
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.exclude(status=MatchmakingQueue.STATUS_CANCELLED).update(
            status=MatchmakingQueue.STATUS_CANCELLED
        )
        self.message_user(request, f"Cancelled {updated} queue entr{'y' if updated == 1 else 'ies'}.")

    @admin.action(description="Reset selected entries to queued")
    def reset_to_queued(self, request, queryset):
        updated = queryset.update(
            status=MatchmakingQueue.STATUS_QUEUED,
            matched_with=None,
            game=None,
        )
        self.message_user(request, f"Reset {updated} queue entr{'y' if updated == 1 else 'ies'} to queued.")


@admin.register(FriendlyChallenge)
class FriendlyChallengeAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'challenger',
        'challengee',
        'title',
        'status',
        'game',
        'created_at',
    ]
    list_filter = ['status', 'title', 'created_at']
    search_fields = [
        'challenger__username',
        'challenger__email',
        'challengee__username',
        'challengee__email',
        'title__name',
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['challenger', 'challengee', 'title', 'challenger_deck', 'challengee_deck', 'game']

    @admin.action(description="Mark selected challenges as cancelled")
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.exclude(status=FriendlyChallenge.STATUS_CANCELLED).update(
            status=FriendlyChallenge.STATUS_CANCELLED
        )
        self.message_user(
            request,
            f"Marked {updated} challenge{'s' if updated != 1 else ''} as cancelled.",
        )

    actions = ['mark_as_cancelled']

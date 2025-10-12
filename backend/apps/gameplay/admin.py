from django.contrib import admin
from .models import Game, GameUpdate


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['id', '__str__', 'status', 'get_game_type', 'get_winner', 'created_at']
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
            'fields': ('status', 'side_a', 'side_b')
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

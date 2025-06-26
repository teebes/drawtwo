from django.contrib import admin
from .models import OwnedCard, OwnedHero, Deck, DeckCard


@admin.register(OwnedCard)
class OwnedCardAdmin(admin.ModelAdmin):
    list_display = ('user', 'card', 'count', 'created_at')
    list_filter = ('created_at', 'card__card_type', 'card__title__status')
    search_fields = ('user__email', 'card__name', 'card__slug', 'card__title__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Ownership', {
            'fields': ('user', 'card', 'count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OwnedHero)
class OwnedHeroAdmin(admin.ModelAdmin):
    list_display = ('user', 'hero', 'created_at')
    list_filter = ('created_at', 'hero__title__status')
    search_fields = ('user__email', 'hero__name', 'hero__slug', 'hero__title__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Ownership', {
            'fields': ('user', 'hero')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class DeckCardInline(admin.TabularInline):
    model = DeckCard
    extra = 0
    fields = ['card', 'count']


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_owner_type', 'owner_name', 'hero', 'get_card_count', 'created_at']
    list_filter = ['hero', 'created_at', 'user', 'ai_player']
    search_fields = ['name', 'user__email', 'ai_player__name', 'hero__name']
    readonly_fields = ['created_at', 'updated_at', 'owner_name', 'is_ai_deck']
    inlines = [DeckCardInline]

    fieldsets = (
        ('Ownership', {
            'fields': ('user', 'ai_player'),
            'description': 'Choose either a user OR an AI player as the deck owner'
        }),
        ('Deck Info', {
            'fields': ('name', 'description', 'hero')
        }),
        ('Info', {
            'fields': ('owner_name', 'is_ai_deck', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_owner_type(self, obj):
        return "👤 Human" if obj.user else "🤖 AI"
    get_owner_type.short_description = "Owner Type"

    def get_card_count(self, obj):
        return obj.cards.count()
    get_card_count.short_description = "Cards"


@admin.register(DeckCard)
class DeckCardAdmin(admin.ModelAdmin):
    list_display = ('deck', 'card', 'count', 'created_at')
    list_filter = ('created_at', 'card__card_type', 'count')
    search_fields = ('deck__name', 'card__name', 'deck__user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Deck Card', {
            'fields': ('deck', 'card', 'count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

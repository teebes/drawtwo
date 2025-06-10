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
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'hero', 'card_count', 'created_at')
    list_filter = ('created_at', 'hero__title__status')
    search_fields = ('name', 'description', 'user__email', 'hero__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    inlines = [DeckCardInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'description')
        }),
        ('Deck Configuration', {
            'fields': ('hero',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def card_count(self, obj):
        """Show total number of cards in the deck"""
        from django.db.models import Sum
        return obj.deckcard_set.aggregate(
            total=Sum('count')
        )['total'] or 0
    card_count.short_description = 'Total Cards'


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

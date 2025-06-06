from django.contrib import admin
from .models import Title, HeroTemplate, CardTemplate


@admin.register(Title)
class TitleAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'version', 'is_latest', 'status', 'author', 'published_at', 'created_at')
    list_filter = ('status', 'is_latest', 'created_at', 'published_at')
    search_fields = ('slug', 'name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('slug', 'name', 'description', 'author')
        }),
        ('Version Control', {
            'fields': ('version', 'is_latest')
        }),
        ('Publishing', {
            'fields': ('status', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(HeroTemplate)
class HeroTemplateAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'health', 'version', 'is_latest', 'created_at')
    list_filter = ('is_latest', 'title__status', 'created_at')
    search_fields = ('slug', 'name', 'description', 'title__slug', 'title__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'name', 'description')
        }),
        ('Version Control', {
            'fields': ('version', 'is_latest')
        }),
        ('Hero Stats', {
            'fields': ('health', 'hero_power')
        }),
        ('Advanced Configuration', {
            'fields': ('spec',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CardTemplate)
class CardTemplateAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'card_type', 'cost', 'attack', 'health', 'version', 'is_latest', 'created_at')
    list_filter = ('card_type', 'is_latest', 'cost', 'title__status', 'created_at')
    search_fields = ('slug', 'name', 'description', 'title__slug', 'title__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'name', 'description')
        }),
        ('Version Control', {
            'fields': ('version', 'is_latest')
        }),
        ('Card Properties', {
            'fields': ('card_type', 'cost')
        }),
        ('Combat Stats', {
            'fields': ('attack', 'health'),
            'description': 'Attack and Health are only applicable to minion cards'
        }),
        ('Advanced Configuration', {
            'fields': ('spec',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Add help text for card type field
        form.base_fields['card_type'].help_text = "Spells don't require attack/health values"
        return form

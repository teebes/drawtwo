from django.contrib import admin
from .models import Title, Tag, Trait, Faction, HeroTemplate, CardTemplate, CardTraitArgument


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


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'title', 'created_at')
    list_filter = ('title', 'created_at')
    search_fields = ('name', 'slug', 'description', 'title__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'name', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Trait)
class TraitAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'title', 'accepts_arguments', 'created_at')
    list_filter = ('title', 'accepts_arguments', 'created_at')
    search_fields = ('name', 'slug', 'description', 'title__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'name', 'description')
        }),
        ('Arguments Configuration', {
            'fields': ('accepts_arguments', 'argument_description'),
            'description': 'Configure whether this trait accepts numeric arguments (e.g., "armor 3")'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Faction)
class FactionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'title', 'created_at')
    list_filter = ('title', 'created_at')
    search_fields = ('name', 'slug', 'description', 'title__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'name', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class CardTraitArgumentInline(admin.TabularInline):
    model = CardTraitArgument
    extra = 0
    fields = ('trait', 'argument', 'extra_data')
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('trait')


@admin.register(CardTraitArgument)
class CardTraitArgumentAdmin(admin.ModelAdmin):
    list_display = ('card', 'trait', 'argument', 'created_at')
    list_filter = ('trait', 'created_at', 'card__title')
    search_fields = ('card__name', 'trait__name', 'card__slug', 'trait__slug')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Relationship', {
            'fields': ('card', 'trait')
        }),
        ('Argument Configuration', {
            'fields': ('argument', 'extra_data')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CardTemplate)
class CardTemplateAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'card_type', 'cost', 'attack', 'health', 'faction', 'version', 'is_latest', 'created_at')
    list_filter = ('card_type', 'is_latest', 'cost', 'faction', 'title__status', 'created_at')
    search_fields = ('slug', 'name', 'description', 'title__slug', 'title__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    filter_horizontal = ('tags', 'traits')
    inlines = [CardTraitArgumentInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'name', 'description')
        }),
        ('Version Control', {
            'fields': ('version', 'is_latest')
        }),
        ('Card Properties', {
            'fields': ('card_type', 'cost', 'faction')
        }),
        ('Combat Stats', {
            'fields': ('attack', 'health'),
            'description': 'Attack and Health are only applicable to minion cards'
        }),
        ('Classification', {
            'fields': ('tags', 'traits'),
            'description': 'Note: Trait arguments are configured in the "Card trait arguments" section below'
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
        if 'traits' in form.base_fields:
            form.base_fields['traits'].help_text = "Select basic traits. Use 'Card trait arguments' section below for traits that need values (e.g., armor 3)"
        return form

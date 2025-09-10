from django.contrib import admin
from .models import Title, Tag, Trait, Faction, HeroTemplate, CardTemplate, CardTrait, AIPlayer, Builder


@admin.register(Title)
class TitleAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'version', 'is_latest', 'status', 'author', 'published_at', 'created_at')
    list_filter = ('status', 'is_latest', 'created_at', 'published_at')
    search_fields = ('slug', 'name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    raw_id_fields = ('author',)

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
    list_display = ('name', 'slug', 'title', 'created_at')
    list_filter = ('title', 'created_at')
    search_fields = ('name', 'slug', 'description', 'title__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    raw_id_fields = ('title',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'name', 'description')
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


class CardTraitInline(admin.TabularInline):
    model = CardTrait
    extra = 0
    fields = ('trait', 'data')
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('trait')


@admin.register(CardTrait)
class CardTraitAdmin(admin.ModelAdmin):
    list_display = ('card', 'trait', 'get_data_summary', 'created_at')
    list_filter = ('trait', 'created_at', 'card__title')
    search_fields = ('card__name', 'trait__name', 'card__slug', 'trait__slug')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Relationship', {
            'fields': ('card', 'trait')
        }),
        ('Trait Data', {
            'fields': ('data',),
            'description': 'JSON data for trait-specific configuration (e.g., {"value": 3} for armor)'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_data_summary(self, obj):
        """Show a summary of the trait data in list view"""
        if not obj.data:
            return "—"
        # Show common patterns nicely
        if 'value' in obj.data and len(obj.data) == 1:
            return f"value: {obj.data['value']}"
        return str(obj.data)
    get_data_summary.short_description = 'Data'


@admin.register(CardTemplate)
class CardTemplateAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'card_type', 'cost', 'attack', 'health', 'faction', 'version', 'is_latest', 'created_at')
    list_filter = ('card_type', 'is_latest', 'cost', 'faction', 'title__status', 'created_at')
    search_fields = ('slug', 'name', 'description', 'title__slug', 'title__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    filter_horizontal = ('tags',)
    inlines = [CardTraitInline]

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
            'fields': ('tags',),
            'description': 'Note: Traits with data are configured in the "Card traits" section below'
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
        # Note: traits field is handled via inline due to through model
        return form


@admin.register(AIPlayer)
class AIPlayerAdmin(admin.ModelAdmin):
    list_display = ['name', 'difficulty', 'created_at']
    list_filter = ['difficulty', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'difficulty')
        }),
        ('AI Strategy', {
            'fields': ('strategy_config',),
            'description': 'AI behavior parameters'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Builder)
class BuilderAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'role', 'added_by', 'created_at')
    list_filter = ('role', 'title__status', 'created_at')
    search_fields = ('title__name', 'title__slug', 'user__email', 'user__username', 'added_by__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Builder Relationship', {
            'fields': ('title', 'user', 'role')
        }),
        ('Metadata', {
            'fields': ('added_by',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Set the current user as default for added_by field when creating new builders
        if not obj and 'added_by' in form.base_fields:
            form.base_fields['added_by'].initial = request.user
        return form

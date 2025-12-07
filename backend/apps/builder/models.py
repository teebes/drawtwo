from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from apps.core.models import TimestampedModel, list_to_choices

User = get_user_model()


class Title(TimestampedModel):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"

    slug = models.SlugField()
    version = models.PositiveIntegerField(default=1)
    is_latest = models.BooleanField(default=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=10,
        choices=list_to_choices([
            STATUS_DRAFT,
            STATUS_PUBLISHED,
            STATUS_ARCHIVED]),
        default=STATUS_DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)

    config = models.JSONField(default=dict)

    class Meta:
        constraints = [
            # One row per (slug, version)
            models.UniqueConstraint(
                fields=["slug", "version"], name="u_slug_version"
            ),
            # Exactly one "latest" row per slug
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(is_latest=True),
                name="u_slug_latest_only_one",
            ),
        ]

    def __str__(self):
        return f"{self.slug} v{self.version}"

    def can_be_edited_by(self, user):
        """Check if a user can edit this title (either author or builder)."""
        if not user or not user.is_authenticated:
            return False

        # Author can always edit
        if self.author == user:
            return True

        # Check if user is a builder for this title
        return self.builders.filter(user=user).exists()

    def can_be_viewed_by(self, user):
        """Check if a user can view this title."""
        # Published titles can be viewed by anyone
        if self.status == self.STATUS_PUBLISHED:
            return True

        # Unpublished titles require authentication
        if not user or not user.is_authenticated:
            return False

        # Author and builders can view unpublished titles
        return self.can_be_edited_by(user)

    @property
    def art_url(self, extension: str = "webp") -> str:
        if settings.USE_R2_FOR_CARDS and settings.CARD_ASSETS_BASE_URL:
            base_url = settings.CARD_ASSETS_BASE_URL.rstrip('/')
            return f"{base_url}/titles/{self.slug}/banner.{extension}"
        else:
            return f"{settings.MEDIA_URL}titles/{self.slug}/banner.{extension}"


class Builder(TimestampedModel):
    """
    Represents a many-to-many relationship between Title and User.
    A Builder can edit cards for a title.
    """
    title = models.ForeignKey(Title, on_delete=models.CASCADE, related_name='builders')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='builder_titles')

    # Additional metadata about the builder relationship
    role = models.CharField(
        max_length=20,
        choices=[
            ('editor', 'Editor'),
            ('collaborator', 'Collaborator'),
        ],
        default='editor',
        help_text="Role of the builder in this title"
    )

    # When this builder was added
    added_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='added_builders',
        help_text="User who added this builder to the title"
    )

    class Meta:
        unique_together = ('title', 'user')
        indexes = [
            models.Index(fields=['title'], name='builder_title_idx'),
            models.Index(fields=['user'], name='builder_user_idx'),
        ]
        verbose_name = "Builder"
        verbose_name_plural = "Builders"

    def __str__(self):
        return f"{self.user} - {self.title} ({self.role})"


class Tag(TimestampedModel):
    title = models.ForeignKey(Title, on_delete=models.PROTECT)
    slug = models.SlugField()
    name = models.CharField(max_length=40)
    description = models.TextField(blank=True)


class Trait(TimestampedModel):
    """
    DEPRECATED: This model is being phased out.

    Trait definitions are now in trait_definitions.py with sparse overrides
    via TraitOverride model. This model is kept for backward compatibility
    and will be removed in a future migration.
    """
    title = models.ForeignKey(Title, on_delete=models.PROTECT)

    # Predefined trait types as constants
    TRAIT_ARMOR = "armor"
    TRAIT_BATTLECRY = "battlecry"
    TRAIT_CHARGE = "charge"
    TRAIT_CLEAVE = "cleave"
    TRAIT_DEATHRATTLE = "deathrattle"
    TRAIT_INSPIRE = "inspire"
    TRAIT_LIFESTEAL = "lifesteal"
    TRAIT_RANGED = "ranged"
    TRAIT_TAUNT = "taunt"
    TRAIT_UNIQUE = "unique"

    slug = models.SlugField(
        choices=list_to_choices([
            TRAIT_ARMOR,
            TRAIT_BATTLECRY,
            TRAIT_CHARGE,
            TRAIT_CLEAVE,
            TRAIT_DEATHRATTLE,
            TRAIT_INSPIRE,
            TRAIT_LIFESTEAL,
            TRAIT_RANGED,
            TRAIT_TAUNT,
            TRAIT_UNIQUE,
        ])
    )
    name = models.CharField(max_length=40, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['name'], name='trait_name_idx'),
        ]


class TraitOverride(TimestampedModel):
    """
    Title-specific customization of trait names and descriptions.

    Stores only overrides; if no override exists, defaults from
    trait_definitions.py are used.
    """
    title = models.ForeignKey(Title, on_delete=models.CASCADE)

    # Import choices from trait_definitions to avoid duplication
    from apps.builder.trait_definitions import TRAIT_SLUGS
    slug = models.SlugField(choices=list_to_choices(TRAIT_SLUGS))

    name = models.CharField(max_length=40)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [['title', 'slug']]
        indexes = [
            models.Index(fields=['title', 'slug'], name='trait_override_title_slug_idx'),
        ]
        verbose_name = "Trait Override"
        verbose_name_plural = "Trait Overrides"

    def __str__(self):
        return f"{self.title.slug}: {self.slug} → {self.name}"


class CardTrait(TimestampedModel):
    """Intermediary table for card-trait assignments with optional data"""
    card = models.ForeignKey('CardTemplate', on_delete=models.CASCADE)

    # Store trait slug directly instead of FK to Trait
    from apps.builder.trait_definitions import TRAIT_SLUGS
    trait_slug = models.SlugField(choices=list_to_choices(TRAIT_SLUGS))

    # Unified data storage for all trait-specific information
    # Examples: {"value": 3} for armor, {"targets": 2} for cleave, {} for simple traits
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ['card', 'trait_slug']
        indexes = [
            models.Index(fields=['card'], name='cardtrait_card_idx'),
            models.Index(fields=['trait_slug'], name='cardtrait_trait_slug_idx'),
        ]
        verbose_name = "Card Trait"
        verbose_name_plural = "Card Traits"

    def __str__(self):
        from apps.builder.trait_definitions import get_trait_info
        trait_info = get_trait_info(self.card.title, self.trait_slug)
        if self.data:
            return f"{self.card.name}: {trait_info['name']} {self.data}"
        return f"{self.card.name}: {trait_info['name']}"

    def get_trait_info(self):
        """Get the trait name and description (with title-specific overrides)."""
        from apps.builder.trait_definitions import get_trait_info
        return get_trait_info(self.card.title, self.trait_slug)


class Faction(TimestampedModel):
    title = models.ForeignKey(Title, on_delete=models.PROTECT)
    slug = models.SlugField()
    name = models.CharField(max_length=40)
    description = models.TextField(blank=True)


class TemplateBase(TimestampedModel):
    title = models.ForeignKey(Title, on_delete=models.PROTECT)
    slug  = models.SlugField()
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    is_latest = models.BooleanField(default=True)

    class Meta:
        abstract = True
        constraints = [
            # unique per title
            models.UniqueConstraint(
                fields=["title", "slug", "version"],
                name="%(class)s_u_title_slug_version",
            ),
            models.UniqueConstraint(
                fields=["title", "slug"],
                condition=models.Q(is_latest=True),
                name="%(class)s_u_title_slug_latest_only_one",
            ),
        ]
        indexes = [models.Index(fields=["title", "slug", "is_latest"], name="%(class)s_t_s_latest_idx")]

    def __str__(self):
        return f"{self.title.slug}:{self.slug} v{self.version}"


class HeroTemplate(TemplateBase):
    health = models.PositiveIntegerField()
    hero_power = models.JSONField(default=dict, blank=True)

    spec = models.JSONField(default=dict, blank=True)

    faction = models.ForeignKey(Faction, on_delete=models.PROTECT,
                                null=True, blank=True)


class CardTemplate(TemplateBase):
    CARD_TYPE_CREATURE = "creature"
    CARD_TYPE_SPELL = "spell"
    card_type = models.CharField(
        max_length=15,
        choices=list_to_choices([
            CARD_TYPE_CREATURE,
            CARD_TYPE_SPELL]),
        default=CARD_TYPE_CREATURE,
    )

    cost = models.PositiveSmallIntegerField(default=0)
    attack = models.PositiveSmallIntegerField(null=True, blank=True)
    health = models.PositiveSmallIntegerField(null=True, blank=True)

    spec = models.JSONField(default=dict, blank=True)

    tags = models.ManyToManyField(Tag, blank=True)
    # traits field removed - use cardtrait_set to access traits
    faction = models.ForeignKey(Faction, on_delete=models.PROTECT,
                                null=True, blank=True)

    is_collectible = models.BooleanField(
        default=True,
        help_text="If False, this card cannot be added to player decks"
    )

    class Meta(TemplateBase.Meta):
        # All indices for CardTemplate organized in one place
        indexes = TemplateBase.Meta.indexes + [
            # Composite index for efficient filtering and ordering
            # Covers: WHERE title=X AND is_latest=Y ORDER BY cost, card_type, attack, health, name
            # Handles: cost grouping -> creatures before spells -> attack/health ordering -> name tie-breaker
            models.Index(fields=['title', 'is_latest', 'cost', 'card_type', 'attack', 'health', 'name'], name='card_full_sort_idx'),
        ]

    def add_trait(self, trait_slug, data=None):
        """
        Add or update a trait by slug.

        Args:
            trait_slug: The trait slug (e.g., 'charge', 'taunt')
            data: Optional dict of trait-specific data
        """
        if data is None:
            data = {}
        card_trait, created = CardTrait.objects.get_or_create(
            card=self,
            trait_slug=trait_slug,
            defaults={'data': data}
        )
        if not created:
            card_trait.data = data
            card_trait.save(update_fields=['data'])

    def get_trait_data(self, trait_slug):
        """Get the data dict for a trait by slug, or empty dict if no data"""
        try:
            return self.cardtrait_set.get(trait_slug=trait_slug).data
        except CardTrait.DoesNotExist:
            return {}

    def get_all_traits_with_data(self):
        """Get all traits as a list of (trait_info, data) tuples"""
        result = []
        for card_trait in self.cardtrait_set.all():
            trait_info = card_trait.get_trait_info()
            result.append((trait_info, card_trait.data))
        return result


class AIPlayer(TimestampedModel):
    """Represents an AI opponent with predefined characteristics"""

    AI_DIFFICULTY_EASY = 'easy'
    AI_DIFFICULTY_MEDIUM = 'medium'
    AI_DIFFICULTY_HARD = 'hard'
    AI_DIFFICULTY_EXPERT = 'expert'

    name = models.CharField(max_length=100)  # e.g., "Aggressive AI", "Control AI"
    difficulty = models.CharField(
        max_length=20,
        choices=[
            (AI_DIFFICULTY_EASY, 'Easy'),
            (AI_DIFFICULTY_MEDIUM, 'Medium'),
            (AI_DIFFICULTY_HARD, 'Hard'),
            (AI_DIFFICULTY_EXPERT, 'Expert'),
        ],
        default=AI_DIFFICULTY_MEDIUM,
    )

    # AI behavior settings
    strategy_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="AI strategy parameters like aggression, card priorities, etc."
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "difficulty"],
                name="ai_player_u_name_difficulty",
            ),
        ]

    def __str__(self):
        return f"🤖 {self.name} ({self.get_difficulty_display()})"


"""
Prototype 'bump version' transactional code:

from django.db import transaction

def bump_version(title_id: int, slug: str, new_data: dict) -> CardTemplate:
    with transaction.atomic():
        # 1 – lock the current latest row
        prev = (CardTemplate.objects
                .select_for_update()
                .get(title_id=title_id, slug=slug, is_latest=True))

        # 2 – mark it no longer latest
        prev.is_latest = False
        prev.save(update_fields=["is_latest"])

        # 3 – insert the new version (is_latest=True)
        return CardTemplate.objects.create(
            title_id = title_id,
            slug     = slug,
            version  = prev.version + 1,
            is_latest=True,
            **new_data
        )

"""
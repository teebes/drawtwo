from django.db import models
from apps.core.models import TimestampedModel, list_to_choices

# Import the User model for foreign key relationships
from django.contrib.auth import get_user_model

User = get_user_model()


class Title(TimestampedModel):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"

    slug = models.SlugField()
    version = models.PositiveIntegerField()
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


class Tag(TimestampedModel):
    title = models.ForeignKey(Title, on_delete=models.PROTECT)
    slug = models.SlugField()
    name = models.CharField(max_length=40)
    description = models.TextField(blank=True)


class Trait(TimestampedModel):
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
    name = models.CharField(max_length=40)
    description = models.TextField(blank=True)

    # Whether this trait type accepts arguments (e.g., armor value)
    accepts_arguments = models.BooleanField(default=False)
    # Description of what the argument represents
    argument_description = models.CharField(max_length=100, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['name'], name='trait_name_idx'),
        ]


class CardTrait(TimestampedModel):
    """Intermediary table for card-trait assignments with optional data"""
    card = models.ForeignKey('CardTemplate', on_delete=models.CASCADE)
    trait = models.ForeignKey(Trait, on_delete=models.CASCADE)

    # Unified data storage for all trait-specific information
    # Examples: {"value": 3} for armor, {"targets": 2} for cleave, {} for simple traits
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ['card', 'trait']
        indexes = [
            models.Index(fields=['card'], name='cardtrait_card_idx'),
            models.Index(fields=['trait'], name='cardtrait_trait_idx'),
        ]
        verbose_name = "Card Trait"
        verbose_name_plural = "Card Traits"

    def __str__(self):
        if self.data:
            return f"{self.card.name}: {self.trait.name} {self.data}"
        return f"{self.card.name}: {self.trait.name}"


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
    CARD_TYPE_MINION = "minion"
    CARD_TYPE_SPELL = "spell"
    card_type = models.CharField(
        max_length=15,
        choices=list_to_choices([
            CARD_TYPE_MINION,
            CARD_TYPE_SPELL]),
        default=CARD_TYPE_MINION,
    )


    cost = models.PositiveSmallIntegerField()
    attack = models.PositiveSmallIntegerField(null=True, blank=True)
    health = models.PositiveSmallIntegerField(null=True, blank=True)

    spec = models.JSONField(default=dict, blank=True)

    tags = models.ManyToManyField(Tag, blank=True)
    traits = models.ManyToManyField(Trait, through='CardTrait', blank=True)
    faction = models.ForeignKey(Faction, on_delete=models.PROTECT,
                                null=True, blank=True)

    class Meta(TemplateBase.Meta):
        # All indices for CardTemplate organized in one place
        indexes = TemplateBase.Meta.indexes + [
            # Composite index for efficient filtering and ordering
            # Covers: WHERE title=X AND is_latest=Y ORDER BY cost, card_type, attack, health, name
            # Handles: cost grouping -> minions before spells -> attack/health ordering -> name tie-breaker
            models.Index(fields=['title', 'is_latest', 'cost', 'card_type', 'attack', 'health', 'name'], name='card_full_sort_idx'),
        ]

    def add_trait(self, trait, data=None):
        """Add a trait with optional data"""
        if data is None:
            data = {}
        CardTrait.objects.get_or_create(
            card=self,
            trait=trait,
            defaults={'data': data}
        )

    def add_trait_with_value(self, trait, value):
        """Add a trait with a simple value (convenience method for backwards compatibility)"""
        self.add_trait(trait, {'value': value})

    def get_trait_data(self, trait):
        """Get the data dict for a trait, or empty dict if no data"""
        try:
            return self.cardtrait_set.get(trait=trait).data
        except CardTrait.DoesNotExist:
            return {}

    def get_trait_value(self, trait):
        """Get the 'value' from trait data, or None if not present (convenience method)"""
        data = self.get_trait_data(trait)
        return data.get('value')

    def get_all_traits_with_data(self):
        """Get all traits as a list of (trait, data) tuples"""
        return [
            (card_trait.trait, card_trait.data)
            for card_trait in self.cardtrait_set.select_related('trait')
        ]


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
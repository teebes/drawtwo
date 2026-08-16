from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from apps.builder.models import AIPlayer, CardTemplate, HeroTemplate, Title
from apps.core.models import TimestampedModel

User = get_user_model()


class OwnedCard(TimestampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card = models.ForeignKey(CardTemplate, on_delete=models.PROTECT)
    count = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "card"],
                name="owned_card_u_user_card",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} → {self.card.name} ({self.count})"


class OwnedHero(TimestampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    hero = models.ForeignKey(HeroTemplate, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "hero"],
                name="owned_hero_u_user_hero",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} → {self.hero.name}"


class DeckQuerySet(models.QuerySet):
    def active(self):
        return self.filter(archived_at__isnull=True)

    def archived(self):
        return self.filter(archived_at__isnull=False)


class Deck(TimestampedModel):
    # Either user-owned or AI-owned (exactly one must be set)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ai_player = models.ForeignKey(
        AIPlayer, on_delete=models.CASCADE, null=True, blank=True
    )

    # Title that this deck belongs to
    title = models.ForeignKey(Title, on_delete=models.PROTECT)

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cards = models.ManyToManyField(CardTemplate, through="DeckCard")
    hero = models.ForeignKey(HeroTemplate, on_delete=models.PROTECT)

    script = models.JSONField(default=dict, blank=True)
    is_pve_opponent = models.BooleanField(
        default=True,
        help_text="Whether this AI deck appears in normal PvE opponent selection.",
    )
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    current_revision = models.ForeignKey(
        "DeckRevision",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="The latest immutable composition/hero revision for this deck.",
    )

    objects = DeckQuerySet.as_manager()

    class Meta:
        constraints = [
            # Ensure exactly one owner
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False, ai_player__isnull=True)
                    | models.Q(user__isnull=True, ai_player__isnull=False)
                ),
                name="deck_exactly_one_owner",
            ),
            # Unique name per user
            models.UniqueConstraint(
                fields=["user", "name"],
                condition=models.Q(user__isnull=False, archived_at__isnull=True),
                name="deck_u_user_name",
            ),
            # Unique name per AI player
            models.UniqueConstraint(
                fields=["ai_player", "name"],
                condition=models.Q(ai_player__isnull=False, archived_at__isnull=True),
                name="deck_u_ai_name",
            ),
        ]

    @property
    def owner(self):
        """Returns the owner (User or AIPlayer)"""
        return self.user or self.ai_player

    @property
    def owner_name(self):
        """Returns displayable owner name"""
        if self.user:
            return self.user.display_name
        return f"🤖 {self.ai_player.name}"

    @property
    def is_ai_deck(self):
        """Returns True if this is an AI-owned deck"""
        return self.ai_player is not None

    @property
    def is_archived(self):
        return self.archived_at is not None

    def archive(self, when=None):
        if self.archived_at:
            return False

        when = when or timezone.now()
        self.archived_at = when
        self.updated_at = when
        self.save(update_fields=["archived_at", "updated_at"])
        return True

    @property
    def deck_size(self):
        """
        Returns the total number of cards in the deck, counting duplicates.
        """
        return self.deckcard_set.aggregate(total=models.Sum("count"))["total"] or 0

    def __str__(self):
        return f"{self.owner_name} → {self.name}"


class UserTitleDeckPreference(TimestampedModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="deck_preferences"
    )
    title = models.ForeignKey(
        Title, on_delete=models.CASCADE, related_name="deck_preferences"
    )
    last_used_deck = models.ForeignKey(
        Deck, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    last_used_friend = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "title"], name="user_title_deck_preference_unique"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "title"]),
        ]

    def __str__(self):
        return f"{self.user.display_name} → {self.title.name}"


class StarterDeckProgram(TimestampedModel):
    """A title's durable new-account eligibility boundary."""

    title_slug = models.SlugField(max_length=255, unique=True)
    eligible_after = models.DateTimeField()

    def __str__(self):
        return f"{self.title_slug} starters after {self.eligible_after.isoformat()}"


class StarterDeckProvisioning(TimestampedModel):
    """Durable state for a starter deck promised to a newly created user."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="starter_deck_provisionings",
    )
    title_slug = models.SlugField(max_length=255)
    deck = models.ForeignKey(
        Deck,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    last_dispatched_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "title_slug"],
                name="starter_deck_provisioning_u_user_title",
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "completed_at"],
                name="starter_deck_user_pending_idx",
            ),
            models.Index(
                fields=[
                    "title_slug",
                    "last_attempted_at",
                    "last_dispatched_at",
                ],
                name="starter_deck_pending_due_idx",
                condition=models.Q(completed_at__isnull=True),
            ),
        ]

    def __str__(self):
        state = "complete" if self.completed_at else "pending"
        return f"{self.user.display_name} → {self.title_slug} ({state})"


class DeckCard(TimestampedModel):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE)
    card = models.ForeignKey(CardTemplate, on_delete=models.PROTECT)
    count = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deck", "card"],
                name="deck_card_u_deck_card",
            ),
        ]

    def __str__(self):
        return f"{self.deck.name} → {self.card.name} ({self.count})"


class DeckComposition(TimestampedModel):
    """A hero-independent, immutable multiset of card slugs."""

    title = models.ForeignKey(
        Title,
        on_delete=models.PROTECT,
        related_name="deck_compositions",
    )
    # Format version for `code`; title + version + digest is the database identity.
    version = models.PositiveSmallIntegerField(default=1)
    # SHA-256 lookup key derived from the title and canonical composition code.
    digest = models.CharField(max_length=64)
    # Canonical, hero-independent, URL-safe signature, e.g. `dt1.bandage~4`.
    code = models.TextField()
    # Parsed `code`, stored as slug/count entries for serialization and validation.
    manifest = models.JSONField(default=list)
    total_cards = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["title", "version", "digest"],
                name="deck_composition_u_title_version_digest",
            )
        ]

    def __str__(self):
        return f"{self.title.slug}: {self.code}"


class DeckCompositionFavorite(TimestampedModel):
    """A user's bookmark of an immutable composition, including public builds."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="deck_composition_favorites",
    )
    composition = models.ForeignKey(
        DeckComposition,
        on_delete=models.CASCADE,
        related_name="favorites",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "composition"],
                name="deck_comp_favorite_u_user_composition",
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "created_at"],
                name="deck_comp_fav_user_created_idx",
            )
        ]

    def __str__(self):
        return f"{self.user.display_name} → {self.composition.code}"


class DeckRevision(TimestampedModel):
    """One immutable occurrence in a mutable deck's gameplay history."""

    SOURCE_CREATE = "create"
    SOURCE_EDIT = "edit"
    SOURCE_RESTORE = "restore"
    SOURCE_IMPORT = "import"
    SOURCE_MIGRATION = "migration"
    SOURCE_GAME = "game"
    SOURCE_CHOICES = [
        (SOURCE_CREATE, "Create"),
        (SOURCE_EDIT, "Edit"),
        (SOURCE_RESTORE, "Restore"),
        (SOURCE_IMPORT, "Import"),
        (SOURCE_MIGRATION, "Migration"),
        (SOURCE_GAME, "Game"),
    ]

    deck = models.ForeignKey(
        Deck,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    sequence = models.PositiveIntegerField()
    composition = models.ForeignKey(
        DeckComposition,
        on_delete=models.PROTECT,
        related_name="revisions",
    )
    hero_slug = models.SlugField(max_length=255)
    hero_name = models.CharField(max_length=120)
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_EDIT,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deck", "sequence"],
                name="deck_revision_u_deck_sequence",
            )
        ]
        indexes = [
            models.Index(
                fields=["composition", "created_at"],
                name="deck_revision_comp_created_idx",
            )
        ]
        ordering = ["deck_id", "sequence"]

    def __str__(self):
        return f"{self.deck.name} r{self.sequence}: {self.composition.code}"

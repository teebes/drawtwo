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


class CardTemplate(TemplateBase):
    CARD_TYPE_MINION = "minion"
    CARD_TYPE_SPELL = "spell"
    card_type = models.CharField(
        max_length=15,
        choices=list_to_choices([
            CARD_TYPE_MINION,
            CARD_TYPE_SPELL]),
        default=CARD_TYPE_MINION,
        db_index=True,
    )

    cost = models.PositiveSmallIntegerField()
    attack = models.PositiveSmallIntegerField(null=True, blank=True)
    health = models.PositiveSmallIntegerField(null=True, blank=True)

    spec = models.JSONField(default=dict, blank=True)



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
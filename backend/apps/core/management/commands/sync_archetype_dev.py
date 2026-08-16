"""Synchronize canonical Archetype content into a development database."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from django.utils import timezone

from apps.builder.models import Title
from apps.builder.schemas import Card, Hero
from apps.builder.services import TitleService
from apps.collection.compositions import parse_composition_code
from apps.collection.provisioning import load_starter_deck_definitions
from apps.core import archetype_dev


class Command(BaseCommand):
    help = (
        "Non-destructively synchronize the tracked Archetype snapshot into a "
        "development database."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("This command can only be run when DEBUG is enabled.")

        manifest_path = archetype_dev.ARCHETYPE_DEV_MANIFEST_PATH
        if not manifest_path.exists():
            raise CommandError(
                f"Missing Archetype development manifest: {manifest_path}"
            )

        yaml_content = manifest_path.read_text(encoding="utf-8")
        with transaction.atomic():
            title, created = self._get_or_create_title()
            service = TitleService(title)
            if created:
                ingested, _ = service.import_snapshot_yaml(
                    yaml_content,
                    replace_missing=False,
                )
            else:
                ingested = service.ingest_resources(
                    self._missing_starter_resources(service, yaml_content)
                )

        action = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"Archetype development content {action}: "
                f"{len(ingested)} resources synchronized; "
                "local-only resources were preserved."
            )
        )

    def _get_or_create_title(self):
        title = (
            Title.objects.filter(slug="archetype", is_latest=True)
            .select_related("author")
            .first()
        )
        if title is not None:
            return title, False

        user_model = get_user_model()
        author, author_created = user_model.objects.get_or_create(
            email=archetype_dev.ARCHETYPE_DEV_AUTHOR_EMAIL,
            defaults={
                "is_active": True,
                "is_email_verified": True,
                "status": user_model.STATUS_APPROVED,
            },
        )
        if author_created:
            author.set_unusable_password()
            author.save(update_fields=["password"])

        latest_version = (
            Title.objects.filter(slug="archetype").aggregate(
                latest=models.Max("version")
            )["latest"]
            or 0
        )
        title = Title.objects.create(
            slug="archetype",
            version=latest_version + 1,
            is_latest=True,
            name="Archetype",
            description="",
            author=author,
            status=Title.STATUS_PUBLISHED,
            published_at=timezone.now(),
        )
        return title, True

    def _missing_starter_resources(self, service, yaml_content):
        definition = next(
            (
                definition
                for definition in load_starter_deck_definitions()
                if definition.title_slug == "archetype"
            ),
            None,
        )
        if definition is None:
            raise CommandError("The Archetype starter-deck manifest is unavailable.")

        resources = service.parse_yaml_resources(yaml_content)
        heroes_by_slug = {
            resource.slug: resource
            for resource in resources
            if isinstance(resource, Hero)
        }
        cards_by_slug = {
            resource.slug: resource
            for resource in resources
            if isinstance(resource, Card)
        }

        missing_hero_slugs = {definition.hero_slug} - set(
            service.title.herotemplate_set.filter(is_latest=True).values_list(
                "slug", flat=True
            )
        )
        required_card_slugs = set(parse_composition_code(definition.composition_code))
        existing_card_slugs = set(
            service.title.cardtemplate_set.filter(is_latest=True).values_list(
                "slug", flat=True
            )
        )
        missing_card_slugs = required_card_slugs - existing_card_slugs

        absent_from_snapshot = (missing_hero_slugs - heroes_by_slug.keys()) | (
            missing_card_slugs - cards_by_slug.keys()
        )
        if absent_from_snapshot:
            label = ", ".join(sorted(absent_from_snapshot))
            raise CommandError(
                "Archetype development snapshot is missing starter resource(s): "
                f"{label}"
            )

        return [heroes_by_slug[slug] for slug in sorted(missing_hero_slugs)] + [
            cards_by_slug[slug] for slug in sorted(missing_card_slugs)
        ]

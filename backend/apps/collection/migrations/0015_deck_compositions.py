import hashlib

import django.db.models.deletion
from django.db import migrations, models

CODE_VERSION = 1
CODE_PREFIX = "dt1"
DIGEST_NAMESPACE = "drawtwo:deck-composition:v1"


def backfill_current_compositions(apps, schema_editor):
    Deck = apps.get_model("collection", "Deck")
    DeckCard = apps.get_model("collection", "DeckCard")
    DeckComposition = apps.get_model("collection", "DeckComposition")
    DeckRevision = apps.get_model("collection", "DeckRevision")

    for deck in Deck.objects.select_related("title", "hero").order_by("id").iterator():
        raw_counts = list(
            DeckCard.objects.filter(deck_id=deck.id)
            .select_related("card")
            .order_by("card__slug")
            .values_list("card__slug", "count")
        )
        totals = {}
        for slug, count in raw_counts:
            totals[slug] = totals.get(slug, 0) + count
        counts = sorted(totals.items())
        if counts:
            entries = ".".join(f"{slug}~{count}" for slug, count in counts)
            code = f"{CODE_PREFIX}.{entries}"
        else:
            code = CODE_PREFIX
        manifest = [{"slug": slug, "count": count} for slug, count in counts]
        total_cards = sum(count for _, count in counts)
        material = f"{DIGEST_NAMESPACE}\0{deck.title.slug}\0{code}"
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()

        composition, _ = DeckComposition.objects.get_or_create(
            title_id=deck.title_id,
            version=CODE_VERSION,
            digest=digest,
            defaults={
                "code": code,
                "manifest": manifest,
                "total_cards": total_cards,
            },
        )
        if (
            composition.code != code
            or composition.manifest != manifest
            or composition.total_cards != total_cards
        ):
            raise RuntimeError("Deck composition digest collision during migration")

        revision = DeckRevision.objects.create(
            deck_id=deck.id,
            sequence=1,
            composition_id=composition.id,
            hero_slug=deck.hero.slug,
            hero_name=deck.hero.name,
            source="migration",
        )
        Deck.objects.filter(pk=deck.id).update(current_revision_id=revision.id)


class Migration(migrations.Migration):

    dependencies = [
        ("collection", "0014_deck_is_pve_opponent"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeckComposition",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.PositiveSmallIntegerField(default=1)),
                ("digest", models.CharField(max_length=64)),
                ("code", models.TextField()),
                ("manifest", models.JSONField(default=list)),
                ("total_cards", models.PositiveIntegerField(default=0)),
                (
                    "title",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="deck_compositions",
                        to="builder.title",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("title", "version", "digest"),
                        name="deck_composition_u_title_version_digest",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="DeckRevision",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("sequence", models.PositiveIntegerField()),
                ("hero_slug", models.SlugField(max_length=255)),
                ("hero_name", models.CharField(max_length=120)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("create", "Create"),
                            ("edit", "Edit"),
                            ("restore", "Restore"),
                            ("import", "Import"),
                            ("migration", "Migration"),
                            ("game", "Game"),
                        ],
                        default="edit",
                        max_length=20,
                    ),
                ),
                (
                    "composition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="revisions",
                        to="collection.deckcomposition",
                    ),
                ),
                (
                    "deck",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="revisions",
                        to="collection.deck",
                    ),
                ),
            ],
            options={
                "ordering": ["deck_id", "sequence"],
                "indexes": [
                    models.Index(
                        fields=["composition", "created_at"],
                        name="deck_revision_comp_created_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("deck", "sequence"),
                        name="deck_revision_u_deck_sequence",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="deck",
            name="current_revision",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "The latest immutable composition/hero revision for this deck."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="collection.deckrevision",
            ),
        ),
        migrations.RunPython(
            backfill_current_compositions,
            migrations.RunPython.noop,
        ),
    ]

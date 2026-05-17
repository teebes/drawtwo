from pathlib import Path
from typing import Any

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.builder.models import CardTemplate
from apps.collection.models import Deck, DeckCard
from apps.collection.validation import validate_deck_for_play


class Command(BaseCommand):
    help = "Replace a deck's card assignment from a YAML manifest."

    def add_arguments(self, parser):
        parser.add_argument("deck_id", type=int)
        parser.add_argument(
            "--input",
            "-i",
            required=True,
            help="Input YAML manifest path.",
        )
        parser.add_argument(
            "--allow-title-mismatch",
            action="store_true",
            help="Apply even if the manifest title slug differs from the deck title.",
        )
        parser.add_argument(
            "--allow-invalid",
            action="store_true",
            help="Save the assignment even if the resulting deck is not legal for play.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and print what would change without writing.",
        )

    def handle(self, *args, **options):
        input_path = Path(options["input"])
        if not input_path.exists():
            raise CommandError(f"Manifest does not exist: {input_path}")

        try:
            deck = Deck.objects.select_related("title", "hero").get(
                id=options["deck_id"]
            )
        except Deck.DoesNotExist as exc:
            raise CommandError(f"Deck {options['deck_id']} does not exist.") from exc

        manifest = yaml.safe_load(input_path.read_text(encoding="utf-8")) or {}
        cards = self._parse_cards(manifest)

        manifest_deck = manifest.get("deck") or {}
        manifest_title = manifest_deck.get("title")
        if (
            manifest_title
            and manifest_title != deck.title.slug
            and not options["allow_title_mismatch"]
        ):
            raise CommandError(
                "Manifest title does not match target deck title: "
                f"{manifest_title!r} != {deck.title.slug!r}. "
                "Pass --allow-title-mismatch to override."
            )

        assignments = self._resolve_assignments(deck, cards)

        with transaction.atomic():
            DeckCard.objects.filter(deck=deck).delete()
            DeckCard.objects.bulk_create(
                [
                    DeckCard(deck=deck, card=card, count=quantity)
                    for card, quantity in assignments
                ]
            )

            validation_error = validate_deck_for_play(deck)
            if validation_error and not options["allow_invalid"]:
                raise CommandError(
                    "Imported assignment is not legal for play; rolled back. "
                    f"{validation_error}. Pass --allow-invalid to save anyway."
                )

            if options["dry_run"]:
                transaction.set_rollback(True)
                if validation_error:
                    self.stdout.write(self.style.WARNING(validation_error))
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Validated {len(assignments)} card assignments for deck {deck.id}"
                    )
                )
                return

        if validation_error:
            self.stdout.write(self.style.WARNING(validation_error))
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(assignments)} card assignments into deck {deck.id}"
            )
        )

    def _parse_cards(self, manifest: dict[str, Any]) -> list[dict[str, Any]]:
        cards = manifest.get("cards")
        if not isinstance(cards, list):
            raise CommandError("Manifest must contain a top-level cards list.")

        parsed_cards = []
        seen_slugs = set()
        for index, card in enumerate(cards, start=1):
            if not isinstance(card, dict):
                raise CommandError(f"cards[{index}] must be a mapping.")

            slug = card.get("slug")
            if not slug:
                raise CommandError(f"cards[{index}] is missing slug.")
            if slug in seen_slugs:
                raise CommandError(f"Duplicate card slug in manifest: {slug}")
            seen_slugs.add(slug)

            raw_quantity = card.get("quantity", card.get("count"))
            try:
                quantity = int(raw_quantity)
            except (TypeError, ValueError) as exc:
                raise CommandError(
                    f"cards[{index}] has invalid quantity: {raw_quantity!r}"
                ) from exc
            if quantity < 1:
                raise CommandError(f"cards[{index}] quantity must be at least 1.")

            parsed_cards.append({"slug": str(slug), "quantity": quantity})

        return parsed_cards

    def _resolve_assignments(self, deck, cards):
        assignments = []
        missing_slugs = []
        for card_manifest in cards:
            slug = card_manifest["slug"]
            card = (
                CardTemplate.objects.filter(
                    title=deck.title,
                    slug=slug,
                )
                .order_by("-is_latest", "-version")
                .first()
            )
            if not card:
                missing_slugs.append(slug)
                continue
            assignments.append((card, card_manifest["quantity"]))

        if missing_slugs:
            raise CommandError(
                "Could not find latest local cards for slug(s): "
                + ", ".join(sorted(missing_slugs))
            )

        return assignments

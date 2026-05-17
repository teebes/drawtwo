from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError

from apps.collection.models import Deck
from apps.collection.validation import validate_deck_for_play


class Command(BaseCommand):
    help = "Export a deck's card assignment to a YAML manifest."

    def add_arguments(self, parser):
        parser.add_argument("deck_id", type=int)
        parser.add_argument(
            "--output",
            "-o",
            required=True,
            help="Output YAML path.",
        )

    def handle(self, *args, **options):
        try:
            deck = (
                Deck.objects.select_related("title", "hero", "user", "ai_player")
                .prefetch_related("deckcard_set__card")
                .get(id=options["deck_id"])
            )
        except Deck.DoesNotExist as exc:
            raise CommandError(f"Deck {options['deck_id']} does not exist.") from exc

        deck_cards = deck.deckcard_set.select_related("card").order_by(
            "card__name", "card__slug"
        )
        validation_error = validate_deck_for_play(deck)
        manifest = {
            "version": 1,
            "deck": {
                "source_id": deck.id,
                "name": deck.name,
                "title": deck.title.slug,
                "hero": deck.hero.slug,
                "owner": deck.owner_name,
                "valid_for_play": validation_error is None,
                "validation_error": validation_error,
            },
            "cards": [
                {
                    "slug": deck_card.card.slug,
                    "name": deck_card.card.name,
                    "version": deck_card.card.version,
                    "is_latest": deck_card.card.is_latest,
                    "quantity": deck_card.count,
                }
                for deck_card in deck_cards
            ],
        }

        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {deck_cards.count()} card assignments to {output_path}"
            )
        )

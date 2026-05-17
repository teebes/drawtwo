from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from django.core.management import CommandError, call_command
from django.test import TestCase

from apps.authentication.models import User
from apps.builder.models import CardTemplate, HeroTemplate, Title
from apps.collection.models import Deck, DeckCard


class DeckManifestCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="deck-tools@example.com",
            username="deck-tools",
        )
        self.title = Title.objects.create(
            slug="manifest-title",
            name="Manifest Title",
            author=self.user,
            config={
                "min_cards_in_deck": 0,
                "deck_card_max_count": 2,
                "deck_size_limit": 10,
            },
        )
        self.hero = HeroTemplate.objects.create(
            title=self.title,
            slug="manifest-hero",
            name="Manifest Hero",
            health=30,
        )
        self.card_a = CardTemplate.objects.create(
            title=self.title,
            slug="card-a",
            name="Card A",
            cost=1,
        )
        self.card_b = CardTemplate.objects.create(
            title=self.title,
            slug="card-b",
            name="Card B",
            cost=2,
        )
        self.deck = Deck.objects.create(
            title=self.title,
            user=self.user,
            name="Manifest Deck",
            hero=self.hero,
        )
        DeckCard.objects.create(deck=self.deck, card=self.card_a, count=2)

    def test_export_deck_manifest_writes_slug_based_yaml(self):
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "deck.yaml"

            call_command(
                "export_deck_manifest",
                self.deck.id,
                output=str(output_path),
                stdout=StringIO(),
            )

            manifest = yaml.safe_load(output_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["deck"]["source_id"], self.deck.id)
        self.assertEqual(manifest["deck"]["title"], self.title.slug)
        self.assertEqual(manifest["cards"][0]["slug"], "card-a")
        self.assertEqual(manifest["cards"][0]["name"], "Card A")
        self.assertEqual(manifest["cards"][0]["version"], 1)
        self.assertEqual(manifest["cards"][0]["is_latest"], True)
        self.assertEqual(manifest["cards"][0]["quantity"], 2)

    def test_import_deck_manifest_replaces_existing_assignment(self):
        manifest = {
            "version": 1,
            "deck": {"title": self.title.slug},
            "cards": [
                {"slug": "card-b", "quantity": 1},
            ],
        }

        with TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "deck.yaml"
            input_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

            call_command(
                "import_deck_manifest",
                self.deck.id,
                input=str(input_path),
                stdout=StringIO(),
            )

        assignments = list(
            self.deck.deckcard_set.select_related("card").values_list(
                "card__slug",
                "count",
            )
        )
        self.assertEqual(assignments, [("card-b", 1)])

    def test_import_deck_manifest_rolls_back_invalid_assignment(self):
        manifest = {
            "version": 1,
            "deck": {"title": self.title.slug},
            "cards": [
                {"slug": "card-b", "quantity": 3},
            ],
        }

        with TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "deck.yaml"
            input_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

            with self.assertRaises(CommandError):
                call_command(
                    "import_deck_manifest",
                    self.deck.id,
                    input=str(input_path),
                    stdout=StringIO(),
                )

        assignments = list(
            self.deck.deckcard_set.select_related("card").values_list(
                "card__slug",
                "count",
            )
        )
        self.assertEqual(assignments, [("card-a", 2)])

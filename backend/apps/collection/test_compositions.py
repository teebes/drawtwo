from django.urls import reverse
from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.builder.models import CardTemplate, HeroTemplate, Title
from apps.collection.compositions import (
    CompositionCodeError,
    encode_composition_code,
    parse_composition_code,
)
from apps.collection.models import Deck, DeckCard, DeckCompositionFavorite, DeckRevision


class CompositionCodeTests(APITestCase):
    def test_encoding_is_order_independent_and_combines_duplicates(self):
        self.assertEqual(
            encode_composition_code([("z-card", 1), ("a-card", 2), ("z-card", 2)]),
            "dt1.a-card~2.z-card~3",
        )
        self.assertEqual(
            parse_composition_code("dt1.a-card~2.z-card~3"),
            {"a-card": 2, "z-card": 3},
        )

    def test_empty_composition_is_dt1(self):
        self.assertEqual(encode_composition_code({}), "dt1")
        self.assertEqual(parse_composition_code("dt1"), {})

    def test_parser_rejects_noncanonical_codes(self):
        for code in (
            "dt1.z~1.a~1",
            "dt1.a~01",
            "dt1.a~0",
            "dt1.a~1.a~2",
            "dt2.a~1",
        ):
            with self.subTest(code=code):
                with self.assertRaises(CompositionCodeError):
                    parse_composition_code(code)

    def test_parser_rejects_counts_that_cannot_be_stored(self):
        for code in (
            "dt1.a~2147483648",
            f"dt1.a~{'9' * 5000}",
            "dt1.a~2147483647.b~1",
        ):
            with self.subTest(code=code[:80]):
                with self.assertRaises(CompositionCodeError):
                    parse_composition_code(code)


class DeckCompositionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="composition-owner@example.com",
            username="composition-owner",
        )
        self.title = Title.objects.create(
            slug="composition-api",
            name="Composition API",
            author=self.user,
            status=Title.STATUS_PUBLISHED,
            config={"deck_card_max_count": 4},
        )
        self.hero_a = HeroTemplate.objects.create(
            title=self.title,
            slug="hero-a",
            name="Hero A",
            health=20,
        )
        self.hero_b = HeroTemplate.objects.create(
            title=self.title,
            slug="hero-b",
            name="Hero B",
            health=20,
        )
        self.card_a = CardTemplate.objects.create(
            title=self.title,
            slug="a-card",
            name="A Card",
            cost=1,
        )
        self.card_b = CardTemplate.objects.create(
            title=self.title,
            slug="b-card",
            name="B Card",
            cost=2,
        )
        self.client.force_authenticate(self.user)

    def _create_deck(self, name="Deck", hero=None):
        response = self.client.post(
            reverse(
                "deck-list-by-title",
                kwargs={"title_slug": self.title.slug},
            ),
            {
                "name": name,
                "description": "",
                "hero_id": (hero or self.hero_a).id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return Deck.objects.get(pk=response.data["id"]), response

    def _add(self, deck, card):
        return self.client.post(
            reverse("add-deck-card", kwargs={"deck_id": deck.id}),
            {"card_slug": card.slug, "count": 1},
            format="json",
        )

    def _delete(self, deck, card):
        return self.client.delete(
            reverse(
                "delete-deck-card",
                kwargs={"deck_id": deck.id, "card_id": card.id},
            )
        )

    def test_create_and_card_mutations_return_current_composition(self):
        deck, created = self._create_deck()
        self.assertEqual(created.data["composition"]["code"], "dt1")
        self.assertFalse(created.data["composition"]["previously_seen"])

        added = self._add(deck, self.card_a)
        self.assertEqual(added.status_code, 200)
        self.assertEqual(added.data["composition"]["code"], "dt1.a-card~1")

        detail = self.client.get(reverse("deck-detail", kwargs={"deck_id": deck.id}))
        self.assertEqual(detail.data["composition"]["code"], "dt1.a-card~1")
        self.assertEqual(detail.data["composition"]["revision"]["sequence"], 2)

    def test_a_b_a_reuses_composition_and_reports_continuity(self):
        deck, _ = self._create_deck()
        first_a = self._add(deck, self.card_a)
        code_a = first_a.data["composition"]["code"]
        self._add(deck, self.card_b)
        self._delete(deck, self.card_b)

        detail = self.client.get(reverse("deck-detail", kwargs={"deck_id": deck.id}))
        self.assertEqual(detail.data["composition"]["code"], code_a)
        self.assertTrue(detail.data["composition"]["previously_seen"])
        deck.refresh_from_db()
        self.assertEqual(deck.revisions.count(), 4)
        self.assertEqual(
            deck.revisions.get(sequence=2).composition_id,
            deck.current_revision.composition_id,
        )

    def test_hero_change_creates_revision_but_reuses_composition(self):
        deck, _ = self._create_deck()
        composition_id = deck.current_revision.composition_id

        response = self.client.put(
            reverse("deck-detail", kwargs={"deck_id": deck.id}),
            {
                "name": deck.name,
                "description": "",
                "hero_id": self.hero_b.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        deck.refresh_from_db()
        self.assertEqual(deck.current_revision.composition_id, composition_id)
        self.assertEqual(deck.current_revision.hero_slug, "hero-b")
        self.assertEqual(deck.revisions.count(), 2)

    def test_rename_only_does_not_create_revision(self):
        deck, _ = self._create_deck()
        revision_id = deck.current_revision_id

        response = self.client.put(
            reverse("deck-detail", kwargs={"deck_id": deck.id}),
            {
                "name": "Renamed",
                "description": "presentation only",
                "hero_id": self.hero_a.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        deck.refresh_from_db()
        self.assertEqual(deck.current_revision_id, revision_id)
        self.assertEqual(deck.revisions.count(), 1)

    def test_identical_composition_in_another_deck_is_existing(self):
        first, _ = self._create_deck("First")
        self._add(first, self.card_a)
        second, _ = self._create_deck("Second", hero=self.hero_b)
        response = self._add(second, self.card_a)

        self.assertTrue(response.data["composition"]["previously_seen"])
        self.assertEqual(response.data["composition"]["occurrence_count"], 2)

    def test_resolve_endpoint_is_read_only(self):
        deck = Deck.objects.create(
            user=self.user,
            title=self.title,
            name="Direct",
            hero=self.hero_a,
        )
        DeckCard.objects.create(deck=deck, card=self.card_a, count=2)
        before = DeckRevision.objects.count()
        response = self.client.get(
            reverse(
                "composition-resolve",
                kwargs={"title_slug": self.title.slug},
            ),
            {"deck": "dt1.a-card~2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["composition"]["code"], "dt1.a-card~2")
        self.assertFalse(response.data["composition"]["is_existing"])
        self.assertEqual(DeckRevision.objects.count(), before)

    def test_favorite_is_idempotent_and_scoped_to_the_player(self):
        code = "dt1.a-card~2"
        favorite_url = reverse(
            "composition-favorite",
            kwargs={"title_slug": self.title.slug, "code": code},
        )

        created = self.client.put(favorite_url)
        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.data["is_favorite"])
        repeated = self.client.put(favorite_url)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(DeckCompositionFavorite.objects.count(), 1)

        resolve_url = reverse(
            "composition-resolve",
            kwargs={"title_slug": self.title.slug},
        )
        resolved = self.client.get(resolve_url, {"deck": code})
        self.assertTrue(resolved.data["composition"]["is_favorite"])

        other_user = User.objects.create_user(
            email="other-composition-player@example.com",
            username="other-composition-player",
        )
        self.client.force_authenticate(other_user)
        resolved_for_other = self.client.get(resolve_url, {"deck": code})
        self.assertFalse(resolved_for_other.data["composition"]["is_favorite"])

        self.client.force_authenticate(self.user)
        removed = self.client.delete(favorite_url)
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(removed.data["is_favorite"])
        self.assertFalse(DeckCompositionFavorite.objects.exists())

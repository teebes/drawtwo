from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.builder.models import Builder, CardTemplate, HeroTemplate, Title
from apps.collection.compositions import ensure_deck_revision
from apps.collection.models import Deck, DeckCard, DeckComposition
from apps.gameplay.models import Game, GameLoadout


class CompositionNameTests(APITestCase):
    def setUp(self):
        self.editor, self.alice, self.bob = [
            User.objects.create_user(email=f"{name}@example.com", username=name)
            for name in ["editor", "alice", "bob"]
        ]
        self.title = Title.objects.create(
            slug="named-compositions",
            name="Named compositions",
            author=self.editor,
            status=Title.STATUS_PUBLISHED,
        )
        hero = HeroTemplate.objects.create(
            title=self.title, slug="hero", name="Hero", health=20
        )
        target = CardTemplate.objects.create(
            title=self.title, slug="target", name="Target", cost=1
        )
        other = CardTemplate.objects.create(
            title=self.title, slug="other", name="Other", cost=2
        )
        self.decks = {}
        for player in [self.editor, self.alice, self.bob]:
            deck = Deck.objects.create(
                user=player, title=self.title, hero=hero, name=f"Private {player.id}"
            )
            DeckCard.objects.create(
                deck=deck, card=other if player == self.editor else target, count=1
            )
            ensure_deck_revision(deck)
            self.decks[player.id] = deck
        self.composition = self.decks[self.alice.id].current_revision.composition
        self.code = self.composition.code
        self.name_url = reverse(
            "composition-name",
            kwargs={"title_slug": self.title.slug, "code": self.code},
        )
        self.stats_url = reverse(
            "composition-stats",
            kwargs={"title_slug": self.title.slug, "code": self.code},
        )

    def _game(self, player, ladder="daily", result="win", **overrides):
        own = self.decks[player.id]
        opponent = self.decks[self.editor.id]
        # Exercise wins from side B as well as the usual side A.
        side = overrides.pop("side", "side_a")
        decks = {side: own, "side_b" if side == "side_a" else "side_a": opponent}
        winner_side = (
            side
            if result == "win"
            else (
                "none"
                if result == "draw"
                else "side_b" if side == "side_a" else "side_a"
            )
        )
        game = Game.objects.create(
            side_a=decks["side_a"],
            side_b=decks["side_b"],
            type=overrides.pop("type", Game.GAME_TYPE_RANKED),
            status=overrides.pop("status", Game.GAME_STATUS_ENDED),
            ladder_type=ladder,
            state={"winner": winner_side},
            winner=decks.get(winner_side),
            **overrides,
        )
        for game_side, deck in decks.items():
            revision, _ = ensure_deck_revision(deck)
            GameLoadout.objects.create(
                game=game,
                side=game_side,
                player=deck.user,
                source_deck=deck,
                source_revision=revision,
                composition=revision.composition,
                hero_slug=revision.hero_slug,
                hero_name=revision.hero_name,
                deck_name=deck.name,
            )
        return game

    def _rename(self, user, name="Control"):
        self.client.force_authenticate(user)
        return self.client.put(self.name_url, {"name": name}, format="json")

    def _can_name(self, user, **filters):
        self.client.force_authenticate(user)
        response = self.client.get(self.stats_url, filters)
        self.assertEqual(response.status_code, 200)
        return response.data["composition"]["can_name"]

    def test_title_editors_keep_access_without_wins_but_staff_do_not(self):
        self.bob.is_staff = True
        self.bob.save(update_fields=["is_staff"])
        for user in [self.alice, self.bob]:
            self.assertFalse(self._can_name(user))
            self.assertEqual(self._rename(user).status_code, 403)
        self.assertTrue(self._can_name(self.editor))
        self.assertEqual(self._rename(self.editor).status_code, 200)
        Builder.objects.create(title=self.title, user=self.alice, added_by=self.editor)
        self.assertTrue(self._can_name(self.alice))
        self.assertEqual(self._rename(self.alice, "Builder name").status_code, 200)
        self.assertFalse(self._can_name(None))
        self.assertEqual(self._rename(None).status_code, 401)

    def test_daily_wins_take_priority_over_more_rapid_wins(self):
        self._game(self.alice)
        for _ in range(3):
            self._game(self.bob, "rapid")
        self.assertTrue(self._can_name(self.alice))
        self.assertEqual(self._rename(self.alice).status_code, 200)
        self.assertFalse(self._can_name(self.bob))
        self.assertEqual(self._rename(self.bob).status_code, 403)

    def test_rapid_breaks_daily_ties_and_permission_is_rechecked_on_save(self):
        self._game(self.alice)
        self._game(self.bob)
        self.assertTrue(self._can_name(self.alice))
        self.assertTrue(self._can_name(self.bob))
        self._game(self.bob, "rapid", side="side_b")
        # Alice's page was opened while she was tied, but she cannot now save.
        self.assertEqual(self._rename(self.alice).status_code, 403)
        self.assertFalse(self._can_name(self.alice))
        self.assertEqual(self._rename(self.bob).status_code, 200)
        self._game(self.alice, "rapid")
        self.assertEqual(self._rename(self.alice, "Tied leader").status_code, 200)
        self.assertEqual(self._rename(self.bob, "Other tied leader").status_code, 200)

    def test_rapid_only_leader_qualifies_and_other_results_do_not_count(self):
        self._game(self.alice, "rapid")
        for _ in range(2):
            self._game(self.bob, type="friendly")
            self._game(self.bob, type="pve")
            self._game(self.bob, status=Game.GAME_STATUS_IN_PROGRESS)
            self._game(self.bob, result="loss")
            self._game(self.bob, result="draw")
        self.assertTrue(self._can_name(self.alice))
        self.assertFalse(self._can_name(self.bob))
        self.assertEqual(self._rename(self.bob).status_code, 403)

    def test_wins_are_all_time_and_survive_deck_edits_and_result_fallback(self):
        game = self._game(self.alice)
        Game.objects.filter(pk=game.id).update(
            created_at=timezone.now() - timedelta(days=365), state={}
        )
        self.decks[self.alice.id].deckcard_set.update(count=2)
        ensure_deck_revision(self.decks[self.alice.id])
        self.assertTrue(
            self._can_name(self.alice, days="7", ladder="rapid", game_type="friendly")
        )
        self.assertEqual(self._rename(self.alice).status_code, 200)
        new_code = self.decks[self.alice.id].current_revision.composition.code
        self.stats_url = reverse(
            "composition-stats",
            kwargs={"title_slug": self.title.slug, "code": new_code},
        )
        self.assertFalse(self._can_name(self.alice))

    def test_names_are_shared_searchable_and_do_not_change_identity(self):
        self._game(self.alice)
        identity = (
            self.composition.code,
            self.composition.digest,
            self.composition.manifest,
        )
        revision_id = self.decks[self.alice.id].current_revision_id
        response = self._rename(self.editor, "  Winter   Control  ")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Winter Control")
        self.composition.refresh_from_db()
        self.assertEqual(
            (self.composition.code, self.composition.digest, self.composition.manifest),
            identity,
        )
        self.assertEqual(self.decks[self.alice.id].revisions.count(), 1)
        self.assertEqual(self.decks[self.alice.id].current_revision_id, revision_id)
        self.client.force_authenticate(None)
        stats = self.client.get(self.stats_url)
        self.assertEqual(stats.data["composition"]["name"], "Winter Control")
        resolved = self.client.get(
            reverse("composition-resolve", kwargs={"title_slug": self.title.slug}),
            {"deck": self.code},
        )
        self.assertEqual(resolved.data["composition"]["name"], "Winter Control")
        browse = self.client.get(
            reverse("composition-list", kwargs={"title_slug": self.title.slug}),
            {"q": "winter"},
        )
        self.assertEqual(browse.data["count"], 1)
        self.assertEqual(
            browse.data["results"][0]["composition"]["name"], "Winter Control"
        )
        other_code = self.decks[self.editor.id].current_revision.composition.code
        matchups = self.client.get(
            reverse(
                "composition-matchups",
                kwargs={"title_slug": self.title.slug, "code": other_code},
            )
        )
        self.assertEqual(
            matchups.data["results"][0]["composition"]["name"], "Winter Control"
        )
        self.client.force_authenticate(self.alice)
        history = self.client.get(f"/api/titles/{self.title.slug}/games/history/")
        self.assertEqual(
            history.data["games"][0]["user_composition"]["name"], "Winter Control"
        )
        detail = self.client.get(
            reverse("deck-detail", kwargs={"deck_id": self.decks[self.alice.id].id})
        )
        self.assertEqual(detail.data["composition"]["name"], "Winter Control")
        self.assertEqual(self._rename(self.editor, "  ").data["name"], "")
        self.assertEqual(
            self.client.get(self.stats_url).data["composition"]["name"], ""
        )

    def test_invalid_names_codes_and_unauthorized_creation_are_rejected(self):
        for value in [None, 1, True, [], {}, "x" * 121]:
            with self.subTest(value=value):
                self.assertEqual(self._rename(self.editor, value).status_code, 400)
        self.assertEqual(self._rename(self.editor, "x" * 120).status_code, 200)
        self.client.force_authenticate(self.editor)
        self.assertEqual(
            self.client.put(self.name_url, {}, format="json").status_code, 400
        )
        count = DeckComposition.objects.count()
        for code in ["invalid", "dt1.foreign-card~1"]:
            url = reverse(
                "composition-name", kwargs={"title_slug": self.title.slug, "code": code}
            )
            self.assertEqual(
                self.client.put(url, {"name": "No"}, format="json").status_code, 400
            )
        new_url = reverse(
            "composition-name",
            kwargs={"title_slug": self.title.slug, "code": "dt1.target~2"},
        )
        self.client.force_authenticate(self.alice)
        self.assertEqual(
            self.client.put(new_url, {"name": "No"}, format="json").status_code, 403
        )
        self.assertEqual(DeckComposition.objects.count(), count)
        self.client.force_authenticate(self.editor)
        self.assertEqual(
            self.client.put(new_url, {"name": "New list"}, format="json").status_code,
            200,
        )
        self.assertEqual(DeckComposition.objects.count(), count + 1)

    def test_access_is_scoped_to_the_title_and_unpublished_titles_stay_private(self):
        other_title = Title.objects.create(
            slug="other-title", name="Other", author=self.bob
        )
        Builder.objects.create(title=other_title, user=self.alice, added_by=self.bob)
        self.assertEqual(self._rename(self.alice).status_code, 403)
        self._game(self.alice)
        self.title.status = Title.STATUS_DRAFT
        self.title.save(update_fields=["status"])
        self.assertEqual(self._rename(self.alice).status_code, 403)
        self.assertEqual(self._rename(self.editor).status_code, 200)

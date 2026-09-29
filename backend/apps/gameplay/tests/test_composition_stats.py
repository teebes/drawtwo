from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.builder.models import CardTemplate, HeroTemplate, Title
from apps.collection.compositions import ensure_deck_revision
from apps.collection.models import Deck, DeckCard, DeckCompositionFavorite
from apps.gameplay.models import Game, GameLoadout
from apps.gameplay.services import GameService


class CompositionStatsTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            email="composition-a@example.com",
            username="composition-a",
        )
        self.user_b = User.objects.create_user(
            email="composition-b@example.com",
            username="composition-b",
        )
        self.title = Title.objects.create(
            slug="composition-title",
            name="Composition Title",
            author=self.user_a,
            status=Title.STATUS_PUBLISHED,
            config={
                "min_cards_in_deck": 1,
                "deck_card_max_count": 4,
            },
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
        self.hero_x = HeroTemplate.objects.create(
            title=self.title,
            slug="hero-x",
            name="Hero X",
            health=20,
        )
        self.hero_y = HeroTemplate.objects.create(
            title=self.title,
            slug="hero-y",
            name="Hero Y",
            health=20,
        )
        self.target_card = CardTemplate.objects.create(
            title=self.title,
            slug="target-card",
            name="Target Card",
            cost=1,
        )
        self.other_card = CardTemplate.objects.create(
            title=self.title,
            slug="other-card",
            name="Other Card",
            cost=1,
        )

        self.deck_a = self._make_deck(
            self.user_a, "Deck A", self.hero_a, self.target_card
        )
        self.deck_b = self._make_deck(
            self.user_b, "Deck B", self.hero_b, self.target_card
        )
        self.opponent_x = self._make_deck(
            self.user_b, "Opponent X", self.hero_x, self.other_card
        )
        self.opponent_y = self._make_deck(
            self.user_b, "Opponent Y", self.hero_y, self.other_card
        )

    def _make_deck(self, user, name, hero, card):
        deck = Deck.objects.create(
            user=user,
            title=self.title,
            name=name,
            hero=hero,
        )
        DeckCard.objects.create(deck=deck, card=card, count=1)
        return deck

    def _create_game(
        self,
        deck_a,
        deck_b,
        *,
        game_type=Game.GAME_TYPE_RANKED,
        status=Game.GAME_STATUS_ENDED,
        winner_side="side_a",
    ):
        game = GameService.create_game(
            deck_a,
            deck_b,
            reuse_active_game=False,
        )
        game.type = game_type
        game.status = status
        state = dict(game.state)
        state["winner"] = winner_side or "none"
        game.state = state
        if winner_side == "side_a":
            game.winner = game.side_a
        elif winner_side == "side_b":
            game.winner = game.side_b
        else:
            game.winner = None
        game.save(update_fields=["type", "status", "state", "winner"])
        return game

    def _stats_url(self, code):
        return reverse(
            "composition-stats",
            kwargs={"title_slug": self.title.slug, "code": code},
        )

    def _browse_url(self):
        return reverse("composition-list", kwargs={"title_slug": self.title.slug})

    def _players_url(self, code):
        return reverse(
            "composition-players",
            kwargs={"title_slug": self.title.slug, "code": code},
        )

    def _matchups_url(self, code):
        return reverse(
            "composition-matchups",
            kwargs={"title_slug": self.title.slug, "code": code},
        )

    def test_browse_sorts_filters_and_paginates_aggregate_records(self):
        self._create_game(self.deck_a, self.opponent_x)
        self._create_game(self.deck_a, self.opponent_x)
        self._create_game(self.deck_a, self.opponent_x, winner_side=None)
        # An unplayed revision must not be discoverable.
        self.deck_b.deckcard_set.update(count=2)
        ensure_deck_revision(self.deck_b, source="edit")

        response = self.client.get(self._browse_url(), {"page_size": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            response.data["summary"],
            {
                "matches": 3,
                "appearances": 6,
                "compositions": 2,
                "record": {
                    "wins": 2,
                    "losses": 2,
                    "draws": 2,
                    "games": 6,
                    "win_rate": 0.3333,
                },
            },
        )
        first = response.data["results"][0]
        self.assertEqual(first["composition"]["code"], "dt1.target-card~1")
        self.assertEqual(
            first["record"],
            {
                "wins": 2,
                "losses": 0,
                "draws": 1,
                "games": 3,
                "win_rate": 0.6667,
            },
        )
        second = self.client.get(self._browse_url(), {"page_size": 1, "page": 2})
        self.assertEqual(second.data["results"][0]["record"]["wins"], 0)
        ascending = self.client.get(self._browse_url(), {"sort": "win_rate_asc"})
        self.assertEqual(ascending.data["results"][0]["record"]["wins"], 0)
        empty = self.client.get(self._browse_url(), {"min_games": 4})
        self.assertEqual(empty.data["results"], [])

    def test_players_group_captured_heroes_and_paginate_without_deck_details(self):
        self._create_game(self.deck_a, self.opponent_x)
        self._create_game(self.deck_a, self.opponent_x)
        self._create_game(self.deck_b, self.opponent_x)
        self.deck_a.hero = self.hero_b
        self.deck_a.save(update_fields=["hero"])
        self._create_game(self.deck_a, self.opponent_x)
        self.hero_a.name = "Renamed Hero A"
        self.hero_a.save(update_fields=["name"])

        response = self.client.get(self._players_url("dt1.target-card~1"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(
            response.data["results"][0],
            {
                "player": {"id": self.user_a.id, "display_name": "composition-a"},
                "hero": {"slug": "hero-a", "name": "Renamed Hero A"},
                "uses": 2,
            },
        )
        self.assertEqual(
            {(r["player"]["id"], r["hero"]["slug"]) for r in response.data["results"]},
            {
                (self.user_a.id, "hero-a"),
                (self.user_a.id, "hero-b"),
                (self.user_b.id, "hero-b"),
            },
        )
        for row in response.data["results"]:
            self.assertEqual(set(row), {"player", "hero", "uses"})
            self.assertEqual(set(row["player"]), {"id", "display_name"})
        for private_value in (
            self.user_a.email,
            self.user_b.email,
            self.deck_a.name,
            self.opponent_x.name,
        ):
            self.assertNotIn(private_value, response.content.decode())
        second = self.client.get(
            self._players_url("dt1.target-card~1"), {"page_size": 1, "page": 2}
        )
        self.assertEqual(second.data["results"], response.data["results"][1:2])

    def test_players_respect_match_filters_and_exclude_unfinished_uses(self):
        old = self._create_game(self.deck_a, self.opponent_x)
        Game.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=30),
            ladder_type=Game.LADDER_TYPE_DAILY,
        )
        recent = self._create_game(self.deck_b, self.opponent_x)
        Game.objects.filter(pk=recent.pk).update(ladder_type=Game.LADDER_TYPE_RAPID)
        self._create_game(
            self.deck_a, self.opponent_x, game_type=Game.GAME_TYPE_FRIENDLY
        )
        self._create_game(
            self.deck_a, self.opponent_x, status=Game.GAME_STATUS_IN_PROGRESS
        )
        self._create_game(self.deck_a, self.opponent_x, status=Game.GAME_STATUS_ABORTED)
        self._create_game(self.deck_a, self.opponent_x, game_type=Game.GAME_TYPE_PVE)
        params = {"days": "7", "ladder": "rapid"}
        response = self.client.get(self._players_url("dt1.target-card~1"), params)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["player"]["id"], self.user_b.id)
        self.assertEqual(response.data["results"][0]["uses"], 1)
        friendly = self.client.get(
            self._players_url("dt1.target-card~1"), {"game_type": "friendly"}
        )
        self.assertEqual(friendly.data["results"][0]["player"]["id"], self.user_a.id)
        self.assertEqual(friendly.data["results"][0]["uses"], 1)

    def test_players_use_safe_display_names_and_skip_missing_players(self):
        game = self._create_game(self.deck_a, self.deck_b)
        self.user_a.username = None
        self.user_a.save(update_fields=["username"])
        self.user_b.deleted_at = timezone.now()
        self.user_b.save(update_fields=["deleted_at"])
        response = self.client.get(self._players_url("dt1.target-card~1"))
        self.assertEqual(
            {row["player"]["display_name"] for row in response.data["results"]},
            {f"Gamer {self.user_a.id}", "Deleted player"},
        )
        for private_value in (
            self.user_a.email,
            self.user_b.email,
            self.user_b.username,
        ):
            self.assertNotIn(private_value, response.content.decode())
        game.loadouts.filter(side=GameLoadout.SIDE_B).update(player=None)
        self.assertEqual(
            self.client.get(self._players_url("dt1.target-card~1")).data["count"], 1
        )

    def test_players_validate_filters_codes_and_title_access(self):
        url = self._players_url("dt1.target-card~1")
        self.assertEqual(self.client.get(url).data["results"], [])
        self.assertEqual(
            self.client.get(self._players_url("invalid-code")).status_code, 400
        )
        for params in (
            {"page": 0},
            {"page_size": 51},
            {"days": "bad"},
            {"ladder": "bad"},
            {"game_type": "pve"},
        ):
            self.assertEqual(self.client.get(url, params).status_code, 400)
        self.title.status = Title.STATUS_DRAFT
        self.title.save(update_fields=["status"])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(self.user_a)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_stats_include_current_energy_costs_and_copy_counts(self):
        self.target_card.cost = 0
        self.target_card.save(update_fields=["cost"])
        self.other_card.cost = 7
        self.other_card.save(update_fields=["cost"])
        response = self.client.get(self._stats_url("dt1.other-card~2.target-card~3"))
        self.assertEqual(response.status_code, 200)
        cards = {card["slug"]: card for card in response.data["composition"]["cards"]}
        self.assertEqual(
            (cards["target-card"]["cost"], cards["target-card"]["count"]), (0, 3)
        )
        self.assertEqual(
            (cards["other-card"]["cost"], cards["other-card"]["count"]), (7, 2)
        )

    def test_browse_searches_card_names_slugs_and_exact_codes(self):
        self._create_game(self.deck_a, self.opponent_x)
        for search in ("TARGET CARD", "target-card", "dt1.target-card~1"):
            with self.subTest(search=search):
                response = self.client.get(self._browse_url(), {"q": search})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["count"], 1)
                self.assertEqual(
                    response.data["results"][0]["composition"]["code"],
                    "dt1.target-card~1",
                )
        response = self.client.get(self._browse_url(), {"q": "absent"})
        self.assertEqual(response.data["count"], 0)

    def test_browse_query_count_is_bounded_and_uses_immutable_captures(self):
        game = self._create_game(self.deck_a, self.opponent_x)
        # Fall back to the winner FK using the same logic as the detail API.
        Game.objects.filter(pk=game.pk).update(state={})
        self.deck_a.deckcard_set.update(count=3)
        ensure_deck_revision(self.deck_a, source="edit")
        with self.assertNumQueries(6):
            response = self.client.get(self._browse_url())
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            response.data["results"][0]["composition"]["code"], "dt1.target-card~1"
        )
        self.assertEqual(response.data["results"][0]["record"]["wins"], 1)
        response = self.client.get(self._matchups_url("dt1.target-card~1"))
        self.assertEqual(response.data["results"][0]["record"]["wins"], 1)

        self.client.force_authenticate(self.user_a)
        with self.assertNumQueries(6):
            personal = self.client.get(self._browse_url(), {"scope": "mine"})
        self.assertEqual(personal.data["count"], 1)
        self.assertEqual(personal.data["results"][0]["record"]["wins"], 1)

    def test_personal_browse_uses_captured_player_not_current_deck_owner(self):
        for winner in ("side_a", "side_b", None):
            self._create_game(self.deck_a, self.opponent_x, winner_side=winner)
        # Ownership and card edits after play must not change attribution.
        self.deck_a.deckcard_set.update(count=3)
        Deck.objects.filter(pk=self.deck_a.pk).update(user=self.user_b)
        for user, own_code in (
            (self.user_a, "dt1.target-card~1"),
            (self.user_b, "dt1.other-card~1"),
        ):
            self.client.force_authenticate(user)
            response = self.client.get(self._browse_url(), {"scope": "mine"})
            self.assertEqual(response.data["scope"], "mine")
            self.assertEqual(response.data["count"], 1)
            row = response.data["results"][0]
            self.assertEqual(row["composition"]["code"], own_code)
            self.assertEqual(
                row["record"],
                {"wins": 1, "losses": 1, "draws": 1, "games": 3, "win_rate": 0.3333},
            )
            self.assertEqual(response.data["summary"]["record"], row["record"])
            self.assertEqual(response.data["summary"]["appearances"], 3)
            self.assertEqual(response.data["summary"]["compositions"], 1)
            # The public default remains community-wide, including the lobby.
            public = self.client.get(self._browse_url())
            self.assertEqual(public.data["scope"], "all")
            self.assertEqual(public.data["count"], 2)

    def test_personal_scope_precedes_sort_minimum_search_and_pagination(self):
        own_other = self._make_deck(
            self.user_a, "Own other", self.hero_a, self.other_card
        )
        self._create_game(self.deck_a, self.opponent_x)
        for _ in range(2):
            self._create_game(own_other, self.deck_b, winner_side="side_b")
        for _ in range(4):
            self._create_game(self.deck_b, self.opponent_x, winner_side="side_b")
        self.client.force_authenticate(self.user_a)
        public = self.client.get(self._browse_url(), {"scope": "all"})
        self.assertEqual(
            public.data["results"][0]["composition"]["code"], "dt1.other-card~1"
        )
        params = {"scope": "mine", "page_size": 1}
        first = self.client.get(self._browse_url(), params)
        self.assertEqual(first.data["count"], 2)
        self.assertEqual(
            first.data["results"][0]["composition"]["code"], "dt1.target-card~1"
        )
        self.assertEqual(first.data["results"][0]["record"]["win_rate"], 1)
        self.assertEqual(first.data["summary"]["record"]["games"], 3)
        self.assertEqual(first.data["summary"]["record"]["wins"], 1)
        for extra in ({"page": 2}, {"sort": "games"}, {"sort": "win_rate_asc"}):
            response = self.client.get(self._browse_url(), {**params, **extra})
            self.assertEqual(
                response.data["results"][0]["composition"]["code"], "dt1.other-card~1"
            )
            self.assertEqual(response.data["results"][0]["record"]["games"], 2)
            self.assertEqual(response.data["results"][0]["record"]["wins"], 0)
        minimum = self.client.get(self._browse_url(), {**params, "min_games": 2})
        self.assertEqual(minimum.data["count"], 1)
        self.assertEqual(minimum.data["results"][0]["record"]["games"], 2)
        search = self.client.get(self._browse_url(), {**params, "q": "target-card"})
        self.assertEqual(search.data["count"], 1)
        self.assertEqual(search.data["results"][0]["record"]["wins"], 1)

    def test_personal_scope_follows_period_ladder_and_game_type(self):
        old = self._create_game(self.deck_a, self.opponent_x)
        Game.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=40), ladder_type="daily"
        )
        recent = self._create_game(self.deck_b, self.opponent_x)
        Game.objects.filter(pk=recent.pk).update(ladder_type="rapid")
        friendly = self._create_game(
            self.deck_a, self.opponent_x, game_type="friendly", winner_side="side_b"
        )
        Game.objects.filter(pk=friendly.pk).update(ladder_type=None)
        self.client.force_authenticate(self.user_a)
        for filters, games, wins in (
            ({"days": "7", "ladder": "rapid"}, 0, 0),
            ({"ladder": "daily"}, 1, 1),
            ({"game_type": "friendly"}, 1, 0),
        ):
            with self.subTest(filters=filters):
                response = self.client.get(
                    self._browse_url(), {"scope": "mine", **filters}
                )
                self.assertEqual(response.data["summary"]["record"]["games"], games)
                self.assertEqual(response.data["summary"]["record"]["wins"], wins)
                if games:
                    row = response.data["results"][0]
                    self.assertEqual(row["record"]["games"], games)
                    self.assertEqual(row["record"]["wins"], wins)
                else:
                    self.assertEqual(response.data["count"], 0)
                    self.assertEqual(response.data["results"], [])

    def test_personal_scope_excludes_ongoing_pve_and_unplayed_revisions(self):
        self._create_game(self.deck_b, self.opponent_x)
        self._create_game(
            self.deck_a, self.opponent_x, status=Game.GAME_STATUS_IN_PROGRESS
        )
        self._create_game(self.deck_a, self.opponent_x, game_type="pve")
        self.client.force_authenticate(self.user_a)
        response = self.client.get(self._browse_url(), {"scope": "mine"})
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["summary"]["appearances"], 0)
        self.assertEqual(response.data["results"], [])

    def test_personal_scope_requires_sign_in_and_valid_scope(self):
        for user in (None, self.user_a):
            self.client.force_authenticate(user)
            self.assertEqual(
                self.client.get(self._browse_url(), {"scope": "unknown"}).status_code,
                400,
            )
            response = self.client.get(self._browse_url(), {"scope": "mine"})
            self.assertEqual(response.status_code, 200 if user else 403)

    def test_favorites_include_unplayed_compositions_and_are_private(self):
        # Community play can supply records even when the saver hasn't played.
        game = self._create_game(self.deck_b, self.opponent_x)
        played = game.loadouts.get(side=GameLoadout.SIDE_A).composition
        self.deck_a.deckcard_set.update(count=2)
        unplayed = ensure_deck_revision(self.deck_a, source="edit")[0].composition
        for composition in (played, unplayed):
            DeckCompositionFavorite.objects.create(
                user=self.user_a, composition=composition
            )
        DeckCompositionFavorite.objects.create(user=self.user_b, composition=played)

        params = {"scope": "favorites"}
        self.assertEqual(self.client.get(self._browse_url(), params).status_code, 403)
        self.client.force_authenticate(self.user_a)
        response = self.client.get(self._browse_url(), params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scope"], "favorites")
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["summary"]["compositions"], 2)
        self.assertEqual(response.data["summary"]["appearances"], 1)
        self.assertEqual(response.data["summary"]["matches"], 1)
        self.assertEqual(
            [row["composition"]["code"] for row in response.data["results"]],
            [played.code, unplayed.code],
        )
        self.assertEqual(response.data["results"][0]["record"]["wins"], 1)
        self.assertEqual(
            response.data["results"][1]["record"],
            {"wins": 0, "losses": 0, "draws": 0, "games": 0, "win_rate": 0.0},
        )

        self.client.force_authenticate(self.user_b)
        other = self.client.get(self._browse_url(), params)
        self.assertEqual(other.data["count"], 1)
        self.assertEqual(other.data["results"][0]["composition"]["code"], played.code)
        self.client.force_authenticate(self.user_a)
        remove_url = reverse(
            "composition-favorite",
            kwargs={"title_slug": self.title.slug, "code": unplayed.code},
        )
        self.assertEqual(self.client.delete(remove_url).status_code, 200)
        self.assertEqual(self.client.get(self._browse_url(), params).data["count"], 1)

    def test_favorites_search_sort_minimum_and_paginate_before_serialization(self):
        game = self._create_game(self.deck_a, self.opponent_x)
        for loadout in game.loadouts.all():
            DeckCompositionFavorite.objects.create(
                user=self.user_a, composition=loadout.composition
            )
        self.deck_a.deckcard_set.update(count=2)
        unplayed = ensure_deck_revision(self.deck_a, source="edit")[0].composition
        unplayed.name = "Future build"
        unplayed.save(update_fields=["name"])
        DeckCompositionFavorite.objects.create(user=self.user_a, composition=unplayed)
        self.client.force_authenticate(self.user_a)
        params = {"scope": "favorites", "page_size": 1}
        for extra, code in (
            ({}, "dt1.target-card~1"),
            ({"sort": "games"}, "dt1.target-card~1"),
            ({"sort": "win_rate_asc"}, "dt1.other-card~1"),
            ({"page": 3}, unplayed.code),
            ({"sort": "win_rate_asc", "page": 3}, unplayed.code),
            ({"q": "Future build"}, unplayed.code),
            ({"q": unplayed.code}, unplayed.code),
            ({"q": "Target Card", "page": 2}, unplayed.code),
        ):
            with self.subTest(extra=extra):
                response = self.client.get(self._browse_url(), {**params, **extra})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data["results"][0]["composition"]["code"], code
                )
                self.assertEqual(response.data["summary"]["compositions"], 3)
        for minimum, count in ((0, 3), (1, 2), (5, 0)):
            response = self.client.get(
                self._browse_url(), {**params, "min_games": minimum}
            )
            self.assertEqual(response.data["count"], count)
        for invalid in ({"min_games": -1}, {"sort": "unknown"}, {"page": 0}):
            self.assertEqual(
                self.client.get(self._browse_url(), {**params, **invalid}).status_code,
                400,
            )

    def test_favorite_records_follow_match_filters_without_hiding_saved_builds(self):
        old = self._create_game(self.deck_b, self.opponent_x)
        composition = old.loadouts.get(side=GameLoadout.SIDE_A).composition
        DeckCompositionFavorite.objects.create(
            user=self.user_a, composition=composition
        )
        Game.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=40), ladder_type="daily"
        )
        self._create_game(
            self.deck_b, self.opponent_x, game_type="friendly", winner_side=None
        )
        self._create_game(
            self.deck_b, self.opponent_x, status=Game.GAME_STATUS_IN_PROGRESS
        )
        self._create_game(self.deck_b, self.opponent_x, game_type="pve")
        self.client.force_authenticate(self.user_a)
        for filters, games, wins, draws in (
            ({"days": "7"}, 0, 0, 0),
            ({"ladder": "rapid"}, 0, 0, 0),
            ({"ladder": "daily"}, 1, 1, 0),
            ({"game_type": "friendly"}, 1, 0, 1),
        ):
            with self.subTest(filters=filters):
                response = self.client.get(
                    self._browse_url(), {"scope": "favorites", **filters}
                )
                self.assertEqual(response.data["count"], 1)
                record = response.data["results"][0]["record"]
                self.assertEqual(record["games"], games)
                self.assertEqual(record["wins"], wins)
                self.assertEqual(record["draws"], draws)
                self.assertEqual(response.data["summary"]["record"], record)

    def test_favorites_respect_title_boundaries_and_access(self):
        composition = ensure_deck_revision(self.deck_a, source="create")[0].composition
        DeckCompositionFavorite.objects.create(
            user=self.user_b, composition=composition
        )
        other_title = Title.objects.create(
            slug="other-title",
            name="Other title",
            author=self.user_a,
            status=Title.STATUS_PUBLISHED,
        )
        self.client.force_authenticate(self.user_b)
        response = self.client.get(
            reverse("composition-list", kwargs={"title_slug": other_title.slug}),
            {"scope": "favorites"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["summary"]["compositions"], 0)
        self.title.status = Title.STATUS_DRAFT
        self.title.save(update_fields=["status"])
        self.assertEqual(
            self.client.get(self._browse_url(), {"scope": "favorites"}).status_code, 403
        )

    def test_browse_and_matchups_never_expose_players_or_source_decks(self):
        game = self._create_game(self.deck_a, self.opponent_x)
        code = game.loadouts.get(side=GameLoadout.SIDE_A).composition.code
        for user in (None, self.user_a, self.user_b):
            self.client.force_authenticate(user)
            for url in (self._browse_url(), self._matchups_url(code)):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                for row in response.data["results"]:
                    expected = {"composition", "record"}
                    self.assertEqual(set(row), expected)
                    self.assertEqual(
                        set(row["composition"]),
                        {
                            "code",
                            "name",
                            "digest",
                            "total_cards",
                            "cards",
                        },
                    )
                payload = response.content.decode()
                for private_value in (
                    self.user_a.email,
                    self.user_a.username,
                    self.user_b.username,
                    self.deck_a.name,
                    self.opponent_x.name,
                ):
                    self.assertNotIn(private_value, payload)

    def test_matchups_group_opposing_compositions_and_mirrors(self):
        game = self._create_game(self.deck_a, self.opponent_x)
        self._create_game(self.deck_a, self.opponent_y, winner_side="side_b")
        self._create_game(self.deck_a, self.deck_b)
        code = game.loadouts.get(side=GameLoadout.SIDE_A).composition.code
        response = self.client.get(self._matchups_url(code))
        self.assertEqual(response.status_code, 200)
        rows = {
            row["composition"]["code"]: row["record"]
            for row in response.data["results"]
        }
        self.assertEqual(set(rows), {code, "dt1.other-card~1"})
        for record in rows.values():
            self.assertEqual(
                record,
                {"wins": 1, "losses": 1, "draws": 0, "games": 2, "win_rate": 0.5},
            )
        self.assertEqual(
            sum(row["games"] for row in rows.values()),
            self.client.get(self._stats_url(code)).data["global"]["games"],
        )
        missing = self._create_game(self.deck_a, self.opponent_x)
        missing.loadouts.filter(side=GameLoadout.SIDE_B).delete()
        response = self.client.get(self._matchups_url(code))
        self.assertEqual(response.data["unattributed_appearances"], 1)

    def test_browse_and_detail_share_period_type_and_ladder_filters(self):
        recent = self._create_game(self.deck_a, self.opponent_x)
        Game.objects.filter(pk=recent.pk).update(ladder_type="rapid")
        old = self._create_game(self.deck_a, self.opponent_x, winner_side="side_b")
        Game.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=40),
            ladder_type="rapid",
        )
        daily = self._create_game(self.deck_a, self.opponent_x, winner_side="side_b")
        Game.objects.filter(pk=daily.pk).update(ladder_type="daily")
        self._create_game(
            self.deck_a, self.opponent_x, game_type="friendly", winner_side="side_b"
        )
        code = recent.loadouts.get(side=GameLoadout.SIDE_A).composition.code
        filters = {"days": "7", "ladder": "rapid"}
        browse = self.client.get(self._browse_url(), filters)
        self.assertEqual(browse.data["summary"]["matches"], 1)
        for url in (self._stats_url(code), self._matchups_url(code)):
            response = self.client.get(url, filters)
            self.assertEqual(response.status_code, 200)
            record = (
                response.data["global"]
                if "global" in response.data
                else response.data["results"][0]["record"]
            )
            self.assertEqual(record["games"], 1)
            self.assertEqual(record["wins"], 1)
        friendly = self.client.get(self._browse_url(), {"game_type": "friendly"})
        self.assertEqual(friendly.data["summary"]["matches"], 1)
        self.assertEqual(
            friendly.data["results"][0]["composition"]["code"], "dt1.other-card~1"
        )

    def test_browse_excludes_unfinished_legacy_and_other_game_types(self):
        self._create_game(self.deck_a, self.opponent_x)
        for game_status in (Game.GAME_STATUS_IN_PROGRESS, Game.GAME_STATUS_ABORTED):
            self._create_game(self.deck_a, self.opponent_x, status=game_status)
        for game_type in (Game.GAME_TYPE_PVE, Game.GAME_TYPE_INTRO):
            self._create_game(self.deck_a, self.opponent_x, game_type=game_type)
        legacy = self._create_game(self.deck_a, self.opponent_x)
        legacy.loadouts.all().delete()
        response = self.client.get(self._browse_url())
        self.assertEqual(response.data["summary"]["matches"], 1)

    def test_public_composition_endpoints_enforce_title_access_and_scope(self):
        self._create_game(self.deck_a, self.opponent_x)
        other = Title.objects.create(
            slug="other-title",
            name="Other",
            author=self.user_a,
            status=Title.STATUS_PUBLISHED,
        )
        response = self.client.get(
            reverse("composition-list", kwargs={"title_slug": other.slug})
        )
        self.assertEqual(response.data["count"], 0)
        self.title.status = Title.STATUS_DRAFT
        self.title.save(update_fields=["status"])
        for url in (self._browse_url(), self._matchups_url("dt1.target-card~1")):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(self.user_a)
        self.assertEqual(self.client.get(self._browse_url()).status_code, 200)

    def test_browse_rejects_invalid_filters_and_handles_empty_data(self):
        self.assertEqual(self.client.get(self._browse_url()).data["count"], 0)
        for key, value in (
            ("days", "oops"),
            ("ladder", "unknown"),
            ("game_type", "pve"),
            ("sort", "unknown"),
            ("page", "0"),
            ("page_size", "51"),
            ("min_games", "-1"),
            ("page", "abc"),
        ):
            with self.subTest(key=key, value=value):
                self.assertEqual(
                    self.client.get(self._browse_url(), {key: value}).status_code, 400
                )
        self.assertEqual(
            self.client.get(self._matchups_url("bad-code")).status_code, 400
        )
        self.assertEqual(
            self.client.get(self._matchups_url("dt1.target-card~1")).data["count"], 0
        )

    def test_game_creation_captures_immutable_loadouts(self):
        game = self._create_game(self.deck_a, self.opponent_x)
        loadout = game.loadouts.get(side=GameLoadout.SIDE_A)
        original_composition = loadout.composition

        self.assertEqual(game.loadouts.count(), 2)
        self.assertEqual(loadout.player, self.user_a)
        self.assertEqual(loadout.source_revision.composition, original_composition)
        self.assertEqual(loadout.hero_slug, "hero-a")
        self.assertEqual(loadout.hero_name, "Hero A")
        self.assertEqual(loadout.deck_name, "Deck A")

        deck_card = self.deck_a.deckcard_set.get(card=self.target_card)
        deck_card.count = 2
        deck_card.save(update_fields=["count"])
        self.deck_a.name = "Renamed Deck"
        self.deck_a.hero = self.hero_b
        self.deck_a.save(update_fields=["name", "hero"])

        later_game = self._create_game(self.deck_a, self.opponent_x)
        later_loadout = later_game.loadouts.get(side=GameLoadout.SIDE_A)
        loadout.refresh_from_db()

        self.assertNotEqual(later_loadout.composition, original_composition)
        self.assertEqual(later_loadout.hero_slug, "hero-b")
        self.assertEqual(later_loadout.deck_name, "Renamed Deck")
        self.assertEqual(loadout.composition, original_composition)
        self.assertEqual(loadout.hero_slug, "hero-a")
        self.assertEqual(loadout.deck_name, "Deck A")

        response = self.client.get(self._stats_url(original_composition.code))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["global"]["games"], 1)
        self.assertEqual(response.data["global"]["wins"], 1)

    def test_stats_default_to_ranked_and_can_filter_friendly(self):
        ranked = self._create_game(
            self.deck_a,
            self.opponent_x,
            game_type=Game.GAME_TYPE_RANKED,
            winner_side="side_a",
        )
        self._create_game(
            self.deck_a,
            self.opponent_x,
            game_type=Game.GAME_TYPE_FRIENDLY,
            winner_side="side_b",
        )
        code = ranked.loadouts.get(side=GameLoadout.SIDE_A).composition.code

        response = self.client.get(self._stats_url(code))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["game_type"], "ranked")
        self.assertEqual(
            response.data["global"],
            {"wins": 1, "losses": 0, "draws": 0, "games": 1, "win_rate": 1.0},
        )
        self.assertIsNone(response.data["player"])

        response = self.client.get(
            self._stats_url(code),
            {"game_type": Game.GAME_TYPE_FRIENDLY},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["global"]["wins"], 0)
        self.assertEqual(response.data["global"]["losses"], 1)

    def test_winner_fk_fallback_matches_headline_and_breakdown_results(self):
        game = self._create_game(self.deck_a, self.opponent_x, winner_side="side_a")
        game.state = {}
        game.save(update_fields=["state"])
        code = game.loadouts.get(side=GameLoadout.SIDE_A).composition.code

        headline = self.client.get(self._stats_url(code))
        breakdown = self.client.get(
            self._stats_url(code),
            {"breakdown": "hero"},
        )

        self.assertEqual(headline.data["global"]["wins"], 1)
        self.assertEqual(headline.data["global"]["losses"], 0)
        self.assertEqual(breakdown.data["global"], headline.data["global"])

    def test_personal_record_is_separate_from_global_record(self):
        won = self._create_game(self.deck_a, self.opponent_x, winner_side="side_a")
        self._create_game(self.deck_b, self.opponent_y, winner_side="side_b")
        code = won.loadouts.get(side=GameLoadout.SIDE_A).composition.code

        self.client.force_authenticate(self.user_a)
        response = self.client.get(self._stats_url(code))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["global"]["games"], 2)
        self.assertEqual(response.data["global"]["wins"], 1)
        self.assertEqual(response.data["global"]["losses"], 1)
        self.assertEqual(response.data["player"]["games"], 1)
        self.assertEqual(response.data["player"]["wins"], 1)
        self.assertEqual(response.data["player"]["losses"], 0)

    def test_stats_report_the_current_players_favorite_state(self):
        revision, _ = ensure_deck_revision(self.deck_a, source="create")
        code = revision.composition.code
        favorite_url = reverse(
            "composition-favorite",
            kwargs={"title_slug": self.title.slug, "code": code},
        )

        self.client.force_authenticate(self.user_a)
        favorite_response = self.client.put(favorite_url)
        self.assertIn(favorite_response.status_code, {200, 201})
        response = self.client.get(self._stats_url(code))
        self.assertTrue(response.data["composition"]["is_favorite"])

        self.client.force_authenticate(self.user_b)
        response = self.client.get(self._stats_url(code))
        self.assertFalse(response.data["composition"]["is_favorite"])

    def test_hero_matchups_group_own_and_opposing_heroes(self):
        first = self._create_game(self.deck_a, self.opponent_x, winner_side="side_a")
        self.deck_b.hero = self.hero_b
        self.deck_b.save(update_fields=["hero"])
        self._create_game(self.deck_b, self.opponent_y, winner_side="side_b")
        code = first.loadouts.get(side=GameLoadout.SIDE_A).composition.code

        self.client.force_authenticate(self.user_a)
        response = self.client.get(
            self._stats_url(code),
            {"breakdown": "hero"},
        )

        self.assertEqual(response.status_code, 200)
        rows = {
            (row["hero"]["slug"], row["opponent_hero"]["slug"]): row
            for row in response.data["hero_matchups"]
        }
        self.assertEqual(set(rows), {("hero-a", "hero-x"), ("hero-b", "hero-y")})
        self.assertEqual(rows[("hero-a", "hero-x")]["global"]["wins"], 1)
        self.assertEqual(rows[("hero-b", "hero-y")]["global"]["losses"], 1)
        self.assertEqual(rows[("hero-a", "hero-x")]["player"]["games"], 1)
        self.assertEqual(rows[("hero-b", "hero-y")]["player"]["games"], 0)

    def test_hero_rename_does_not_split_matchup_group(self):
        first = self._create_game(self.deck_a, self.opponent_x, winner_side="side_a")
        self.hero_a.name = "Renamed Hero A"
        self.hero_a.save(update_fields=["name"])
        self._create_game(self.deck_a, self.opponent_x, winner_side="side_b")
        code = first.loadouts.get(side=GameLoadout.SIDE_A).composition.code

        response = self.client.get(
            self._stats_url(code),
            {"breakdown": "hero"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["hero_matchups"]), 1)
        matchup = response.data["hero_matchups"][0]
        self.assertEqual(matchup["hero"]["slug"], "hero-a")
        self.assertEqual(matchup["hero"]["name"], "Renamed Hero A")
        self.assertEqual(matchup["global"]["games"], 2)
        self.assertEqual(matchup["global"]["wins"], 1)
        self.assertEqual(matchup["global"]["losses"], 1)

    def test_legacy_and_unfinished_games_are_excluded(self):
        ended = self._create_game(self.deck_a, self.opponent_x, winner_side="side_a")
        self._create_game(
            self.deck_a,
            self.opponent_x,
            status=Game.GAME_STATUS_IN_PROGRESS,
            winner_side=None,
        )
        self._create_game(
            self.deck_a,
            self.opponent_x,
            status=Game.GAME_STATUS_ABORTED,
            winner_side=None,
        )
        Game.objects.create(
            type=Game.GAME_TYPE_RANKED,
            status=Game.GAME_STATUS_ENDED,
            side_a=self.deck_a,
            side_b=self.opponent_x,
            winner=self.deck_a,
            state={"winner": "side_a"},
        )
        code = ended.loadouts.get(side=GameLoadout.SIDE_A).composition.code

        response = self.client.get(self._stats_url(code))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["global"]["games"], 1)
        self.assertEqual(response.data["attribution"]["captured_games"], 1)
        self.assertTrue(response.data["attribution"]["legacy_games_excluded"])

    def test_mirror_match_counts_one_win_and_one_loss(self):
        game = self._create_game(self.deck_a, self.deck_b, winner_side="side_a")
        code = game.loadouts.get(side=GameLoadout.SIDE_A).composition.code

        response = self.client.get(self._stats_url(code))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["global"]["games"], 2)
        self.assertEqual(response.data["global"]["wins"], 1)
        self.assertEqual(response.data["global"]["losses"], 1)
        self.assertEqual(response.data["attribution"]["captured_games"], 1)

    def test_invalid_composition_code_returns_400(self):
        response = self.client.get(self._stats_url("not-a-composition-code"))

        self.assertEqual(response.status_code, 400)

    def test_valid_unseen_composition_code_returns_zero_stats(self):
        unused_card = CardTemplate.objects.create(
            title=self.title,
            slug="unused-card",
            name="Unused Card",
            cost=1,
        )
        unused_deck = self._make_deck(
            self.user_a,
            "Unused Deck",
            self.hero_a,
            unused_card,
        )
        revision, _ = ensure_deck_revision(unused_deck, source="create")
        composition = revision.composition
        code = composition.code

        unused_deck.current_revision = None
        unused_deck.save(update_fields=["current_revision"])
        revision.delete()
        composition.delete()

        response = self.client.get(self._stats_url(code))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["composition"]["code"], code)
        self.assertEqual(response.data["global"]["games"], 0)
        self.assertEqual(response.data["global"]["win_rate"], 0.0)
        self.assertIsNone(response.data["attribution"]["first_captured_at"])

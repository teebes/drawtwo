from django.urls import reverse
from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.builder.models import CardTemplate, HeroTemplate, Title
from apps.collection.compositions import ensure_deck_revision
from apps.collection.models import Deck, DeckCard
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

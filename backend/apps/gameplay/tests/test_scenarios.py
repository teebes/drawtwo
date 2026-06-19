from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.builder.models import CardTemplate, CardTrait, HeroTemplate, Title
from apps.gameplay.models import Game
from apps.gameplay.scenarios import ScenarioGameService
from apps.gameplay.schemas.game import GameState
from apps.gameplay.services import GameService

User = get_user_model()


class IntroScenarioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="scenario@example.com",
            username="scenario",
        )
        self.title = Title.objects.create(
            slug="archetype",
            version=1,
            is_latest=True,
            name="Archetype",
            author=self.user,
            status=Title.STATUS_PUBLISHED,
            config={
                "deck_size_limit": 30,
                "min_cards_in_deck": 10,
                "deck_card_max_count": 9,
                "hand_start_size": 3,
                "side_b_compensation": None,
                "death_retaliation": False,
                "ranked_time_per_turn": 60,
            },
        )
        self.create_intro_content()

    def create_card(
        self,
        slug,
        *,
        card_type="creature",
        cost=1,
        attack=0,
        health=0,
        traits=None,
        is_collectible=True,
    ):
        card = CardTemplate.objects.create(
            title=self.title,
            slug=slug,
            name=slug.replace("-", " ").title(),
            card_type=card_type,
            cost=cost,
            attack=attack,
            health=health,
            is_collectible=is_collectible,
        )
        for trait in traits or []:
            trait_data = dict(trait)
            trait_slug = trait_data.pop("type")
            CardTrait.objects.create(
                card=card,
                trait_slug=trait_slug,
                data=trait_data,
            )
        return card

    def create_intro_content(self):
        HeroTemplate.objects.create(
            title=self.title,
            slug="commander",
            name="Commander",
            health=30,
            hero_power={
                "name": "Rally",
                "cost": 1,
                "actions": [{"action": "summon", "target": "recruit"}],
            },
        )
        HeroTemplate.objects.create(
            title=self.title,
            slug="berserker",
            name="Berserker",
            health=30,
            hero_power={
                "name": "Rage",
                "cost": 1,
                "actions": [
                    {
                        "action": "damage",
                        "amount": 1,
                        "target": "enemy",
                        "scope": "single",
                        "damage_type": "spell",
                    }
                ],
            },
        )

        self.create_card("mongoose", cost=1, attack=1, health=2)
        self.create_card(
            "decoy", cost=2, attack=1, health=3, traits=[{"type": "taunt"}]
        )
        self.create_card("brute", cost=3, attack=3, health=4)
        self.create_card("soldier", cost=4, attack=4, health=5)
        self.create_card(
            "archer", cost=2, attack=2, health=1, traits=[{"type": "ranged"}]
        )
        self.create_card(
            "knight", cost=6, attack=6, health=4, traits=[{"type": "charge"}]
        )
        self.create_card("recruit", cost=0, attack=1, health=1, is_collectible=False)
        self.create_card(
            "shield", cost=0, attack=0, health=4, traits=[{"type": "taunt"}]
        )
        self.create_card(
            "spear", cost=0, attack=3, health=3, traits=[{"type": "ranged"}]
        )

        self.create_card(
            "powerup",
            card_type="spell",
            cost=0,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [{"action": "temp_mana_boost", "amount": 1}],
                }
            ],
        )
        self.create_card(
            "sharpen",
            card_type="spell",
            cost=1,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [
                        {
                            "action": "buff",
                            "attribute": "attack",
                            "amount": 3,
                            "target": "creature",
                            "scope": "single",
                        }
                    ],
                }
            ],
        )
        self.create_card(
            "cleave",
            card_type="spell",
            cost=2,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [
                        {
                            "action": "damage",
                            "amount": 2,
                            "target": "enemy",
                            "scope": "cleave",
                        }
                    ],
                }
            ],
        )
        self.create_card(
            "mine",
            cost=3,
            attack=2,
            health=1,
            traits=[
                {
                    "type": "deathrattle",
                    "actions": [
                        {
                            "action": "damage",
                            "amount": 1,
                            "target": "enemy",
                            "scope": "all",
                            "damage_type": "spell",
                        }
                    ],
                }
            ],
        )
        self.create_card(
            "drawtwo",
            card_type="spell",
            cost=3,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [{"action": "draw", "amount": 2}],
                }
            ],
        )
        self.create_card(
            "grenade",
            card_type="spell",
            cost=3,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [
                        {
                            "action": "damage",
                            "amount": 2,
                            "target": "enemy",
                            "scope": "all",
                        }
                    ],
                }
            ],
        )
        self.create_card(
            "medic",
            cost=4,
            attack=3,
            health=3,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [
                        {
                            "action": "heal",
                            "amount": 3,
                            "target": "friendly",
                            "scope": "single",
                        }
                    ],
                }
            ],
        )
        self.create_card(
            "remove",
            card_type="spell",
            cost=4,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [{"action": "remove", "target": "enemy"}],
                }
            ],
        )
        self.create_card(
            "phalanx",
            card_type="spell",
            cost=4,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [
                        {"action": "summon", "target": "shield"},
                        {"action": "summon", "target": "spear"},
                    ],
                },
                {"type": "unique"},
            ],
        )
        self.create_card(
            "cheerleader",
            cost=3,
            attack=2,
            health=2,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [
                        {
                            "action": "buff",
                            "attribute": "health",
                            "amount": 2,
                            "target": "creature",
                            "scope": "all",
                        }
                    ],
                },
                {"type": "unique"},
            ],
        )
        self.create_card(
            "meteor",
            card_type="spell",
            cost=6,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [
                        {
                            "action": "damage",
                            "amount": 4,
                            "target": "enemy",
                            "scope": "single",
                        },
                        {
                            "action": "damage",
                            "amount": 2,
                            "target": "enemy",
                            "scope": "all",
                        },
                    ],
                }
            ],
        )
        self.create_card(
            "ambusher",
            cost=4,
            attack=4,
            health=4,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [
                        {
                            "action": "damage",
                            "amount": 1,
                            "target": "enemy",
                            "scope": "single",
                            "damage_type": "spell",
                        }
                    ],
                }
            ],
        )
        self.create_card(
            "zap",
            card_type="spell",
            cost=1,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [
                        {
                            "action": "damage",
                            "amount": 2,
                            "target": "enemy",
                            "scope": "single",
                        }
                    ],
                }
            ],
        )
        self.create_card(
            "bandage",
            card_type="spell",
            cost=1,
            traits=[
                {
                    "type": "battlecry",
                    "actions": [
                        {
                            "action": "heal",
                            "amount": 3,
                            "target": "friendly",
                        }
                    ],
                }
            ],
        )
        self.create_card(
            "harbinger",
            cost=2,
            attack=1,
            health=2,
            traits=[
                {
                    "type": "deathrattle",
                    "actions": [{"action": "draw", "amount": 1}],
                }
            ],
        )
        self.create_card(
            "shieldwall",
            cost=5,
            attack=3,
            health=7,
            traits=[{"type": "taunt"}],
        )
        self.create_card(
            "phoenix",
            cost=7,
            attack=5,
            health=5,
            traits=[
                {
                    "type": "deathrattle",
                    "actions": [{"action": "summon", "target": "phoenix"}],
                },
                {"type": "unique"},
            ],
        )

    def slugs_for(self, state, zone):
        return [state.cards[card_id].template_slug for card_id in zone]

    def test_intro_scenario_builds_ordered_game_state(self):
        game, token = ScenarioGameService.start_scenario("intro-archetype-v1")
        state = GameState.model_validate(game.state)

        self.assertEqual(game.type, Game.GAME_TYPE_INTRO)
        self.assertTrue(game.allows_guest_access(token))
        self.assertFalse(game.allows_guest_access("wrong-token"))
        self.assertEqual(game.guest_access_side, "side_b")
        self.assertEqual(state.ai_sides, ["side_a"])
        self.assertEqual(state.heroes["side_a"].template_slug, "commander")
        self.assertEqual(state.heroes["side_a"].health, 10)
        self.assertEqual(state.heroes["side_a"].health_max, 10)
        self.assertEqual(state.heroes["side_b"].template_slug, "berserker")
        self.assertEqual(state.heroes["side_b"].health, 10)
        self.assertEqual(self.slugs_for(state, state.hands["side_a"]), [])
        self.assertEqual(
            self.slugs_for(state, state.hands["side_b"]),
            ["powerup", "decoy", "bandage"],
        )
        self.assertEqual(
            self.slugs_for(state, state.decks["side_a"]),
            [
                "sharpen",
                "decoy",
                "brute",
                "grenade",
                "mine",
                "archer",
                "medic",
                "cheerleader",
                "decoy",
                "shieldwall",
                "phoenix",
            ],
        )
        self.assertEqual(
            self.slugs_for(state, state.decks["side_b"]),
            [
                "mongoose",
                "harbinger",
                "brute",
                "phalanx",
                "cleave",
                "drawtwo",
                "remove",
                "archer",
                "shieldwall",
                "ambusher",
                "zap",
                "knight",
                "phoenix",
                "soldier",
            ],
        )

    def test_guest_token_can_view_intro_game(self):
        game, token = ScenarioGameService.start_scenario("intro-archetype-v1")
        url = f"/api/gameplay/games/{game.id}/"

        denied = self.client.get(url)
        self.assertEqual(denied.status_code, 403)

        allowed = self.client.get(url, HTTP_X_GAME_ACCESS_TOKEN=token)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.data["viewer"], "side_b")
        self.assertEqual(allowed.data["game_type"], Game.GAME_TYPE_INTRO)

        allowed_with_query_token = self.client.get(url, {"guest_token": token})
        self.assertEqual(allowed_with_query_token.status_code, 200)
        self.assertEqual(allowed_with_query_token.data["viewer"], "side_b")

    def test_intro_endpoint_starts_game(self):
        response = self.client.post("/api/gameplay/scenarios/intro-archetype-v1/start/")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["game_type"], Game.GAME_TYPE_INTRO)
        self.assertEqual(response.data["title_slug"], "archetype")
        self.assertEqual(response.data["viewer_side"], "side_b")
        self.assertTrue(response.data["access_token"])

    @override_settings(GAMEPLAY_AI_COMMAND_DELAY_SECONDS=1.25)
    def test_intro_ai_commands_are_scheduled_with_configured_delay(self):
        game, _ = ScenarioGameService.start_scenario("intro-archetype-v1")

        with patch("apps.gameplay.tasks.step.apply_async") as mock_apply_async:
            GameService.step(game.id)

        mock_apply_async.assert_called_once_with(args=[game.id], countdown=1.25)
        game.refresh_from_db()
        state = GameState.model_validate(game.state)
        self.assertEqual(state.active, "side_a")
        self.assertEqual(state.phase, "main")
        self.assertEqual(len(game.queue), 1)

    def test_intro_games_do_not_break_title_games_list(self):
        game, _ = ScenarioGameService.start_scenario("intro-archetype-v1")

        response = self.client.get("/api/titles/archetype/games/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["games"][0]["id"], game.id)
        self.assertEqual(response.data["games"][0]["type"], Game.GAME_TYPE_INTRO)

    def test_intro_ai_uses_scripted_opening_then_passes_turn(self):
        game, _ = ScenarioGameService.start_scenario("intro-archetype-v1")

        GameService.step(game.id)
        game.refresh_from_db()
        state = GameState.model_validate(game.state)

        self.assertEqual(state.active, "side_b")
        self.assertEqual(state.phase, "main")
        self.assertEqual(state.turn, 1)
        self.assertEqual(len(state.board["side_a"]), 1)
        recruit = state.creatures[state.board["side_a"][0]]
        self.assertEqual(recruit.name, "Recruit")
        self.assertEqual(recruit.attack, 1)
        self.assertEqual(self.slugs_for(state, state.hands["side_a"]), ["sharpen"])

        GameService.process_command(game.id, {"type": "cmd_end_turn"}, "side_b")
        GameService.step(game.id)
        game.refresh_from_db()
        state = GameState.model_validate(game.state)

        self.assertEqual(state.active, "side_b")
        self.assertEqual(state.phase, "main")
        self.assertEqual(state.turn, 2)
        self.assertEqual(len(state.board["side_a"]), 2)
        new_recruit = state.creatures[state.board["side_a"][0]]
        buffed_recruit = state.creatures[state.board["side_a"][1]]
        self.assertEqual(new_recruit.name, "Recruit")
        self.assertEqual(new_recruit.attack, 1)
        self.assertFalse(new_recruit.exhausted)
        self.assertEqual(buffed_recruit.name, "Recruit")
        self.assertEqual(buffed_recruit.attack, 4)
        self.assertFalse(buffed_recruit.exhausted)
        self.assertEqual(state.heroes["side_b"].health, 6)
        self.assertEqual(self.slugs_for(state, state.graveyard["side_a"]), ["sharpen"])

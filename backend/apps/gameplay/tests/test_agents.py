from django.test import TestCase

from apps.builder.schemas import DamageAction, DrawAction, HeroPower, Taunt
from apps.gameplay.agents.legal import list_legal_commands
from apps.gameplay.agents.observation import filter_state_for_player, make_observation
from apps.gameplay.agents.simulator import apply_command
from apps.gameplay.schemas.commands import AttackCommand, UseHeroCommand
from apps.gameplay.schemas.game import CardInPlay, Creature, GameState, HeroInPlay


def make_agent_test_state() -> GameState:
    return GameState(
        turn=1,
        active="side_a",
        phase="main",
        cards={
            "card_a_1": CardInPlay(
                card_id="card_a_1",
                card_type="creature",
                template_slug="ai-creature",
                name="AI Creature",
                attack=2,
                health=2,
                cost=1,
            ),
            "card_b_1": CardInPlay(
                card_id="card_b_1",
                card_type="creature",
                template_slug="enemy-creature",
                name="Enemy Creature",
                attack=1,
                health=3,
                cost=1,
            ),
        },
        creatures={
            "creature_a_1": Creature(
                creature_id="creature_a_1",
                card_id="card_a_1",
                name="AI Creature",
                attack=2,
                health=2,
                exhausted=False,
            ),
            "creature_b_1": Creature(
                creature_id="creature_b_1",
                card_id="card_b_1",
                name="Enemy Creature",
                attack=1,
                health=3,
                exhausted=False,
            ),
        },
        board={
            "side_a": ["creature_a_1"],
            "side_b": ["creature_b_1"],
        },
        heroes={
            "side_a": HeroInPlay(
                hero_id="hero_a",
                template_slug="hero-a",
                name="Hero A",
                health=10,
                hero_power=HeroPower(name="Draw", actions=[]),
                exhausted=True,
            ),
            "side_b": HeroInPlay(
                hero_id="hero_b",
                template_slug="hero-b",
                name="Hero B",
                health=10,
                hero_power=HeroPower(
                    name="Ping",
                    actions=[DamageAction(amount=1, target="enemy")],
                ),
                exhausted=True,
            ),
        },
        hands={"side_a": ["card_a_1"], "side_b": ["card_b_1"]},
        decks={"side_a": ["deck_a_1"], "side_b": ["deck_b_1", "deck_b_2"]},
        graveyard={"side_a": [], "side_b": []},
        mana_pool={"side_a": 10, "side_b": 10},
        mana_used={"side_a": 0, "side_b": 0},
    )


class AgentObservationTests(TestCase):
    def test_filter_state_hides_opponent_hidden_zones_but_preserves_counts(self):
        state = make_agent_test_state()

        filtered = filter_state_for_player(state, "side_a")

        self.assertEqual(filtered["hands"]["side_a"], ["card_a_1"])
        self.assertNotEqual(filtered["hands"]["side_b"], ["card_b_1"])
        self.assertEqual(len(filtered["hands"]["side_b"]), 1)
        self.assertEqual(filtered["hand_counts"]["side_b"], 1)
        self.assertEqual(len(filtered["decks"]["side_a"]), 1)
        self.assertEqual(len(filtered["decks"]["side_b"]), 2)
        self.assertNotEqual(filtered["decks"]["side_b"], ["deck_b_1", "deck_b_2"])

    def test_agent_observation_redacts_hidden_card_records(self):
        state = make_agent_test_state()
        state.cards["hidden_b_1"] = CardInPlay(
            card_id="hidden_b_1",
            card_type="creature",
            template_slug="hidden-enemy-card",
            name="Hidden Enemy Card",
            attack=9,
            health=9,
            cost=9,
        )
        state.hands["side_b"].append("hidden_b_1")

        observation = make_observation(state, "side_a")

        self.assertIn("card_a_1", observation.public_state["cards"])
        self.assertNotIn("hidden_b_1", observation.public_state["cards"])


class LegalCommandTests(TestCase):
    def test_attack_commands_respect_taunt(self):
        state = make_agent_test_state()
        taunt = Creature(
            creature_id="taunt_b_1",
            card_id="card_b_1",
            name="Taunt",
            attack=1,
            health=4,
            traits=[Taunt()],
            exhausted=False,
        )
        state.creatures[taunt.creature_id] = taunt
        state.board["side_b"].append(taunt.creature_id)

        commands = list_legal_commands(state, "side_a")
        attack_commands = [
            command for command in commands if isinstance(command, AttackCommand)
        ]

        self.assertTrue(attack_commands)
        self.assertEqual(
            {command.target_id for command in attack_commands},
            {"taunt_b_1"},
        )

    def test_listed_attack_command_simulates_without_error(self):
        state = make_agent_test_state()
        command = next(
            command
            for command in list_legal_commands(state, "side_a")
            if isinstance(command, AttackCommand) and command.target_type == "hero"
        )

        result = apply_command(state, "side_a", command)

        self.assertFalse(result.errors)
        self.assertEqual(result.state.heroes["side_b"].health, 8)
        self.assertTrue(result.state.creatures["creature_a_1"].exhausted)

    def test_no_target_hero_power_uses_validation_safe_placeholder(self):
        state = make_agent_test_state()
        state.heroes["side_a"].exhausted = False
        state.heroes["side_a"].hero_power = HeroPower(
            name="Draw",
            actions=[DrawAction(amount=1)],
        )

        command = next(
            command
            for command in list_legal_commands(state, "side_a")
            if command.type == "cmd_use_hero"
        )
        result = apply_command(state, "side_a", command)

        self.assertFalse(result.errors)

    def test_friendly_damage_hero_power_lists_own_targets(self):
        state = make_agent_test_state()
        state.heroes["side_a"].exhausted = False
        state.heroes["side_a"].hero_power = HeroPower(
            name="Pact",
            actions=[
                DamageAction(amount=1, target="friendly"),
                DrawAction(amount=1),
            ],
        )

        commands = [
            command
            for command in list_legal_commands(state, "side_a")
            if isinstance(command, UseHeroCommand)
        ]

        self.assertEqual(
            {(command.target_type, command.target_id) for command in commands},
            {("creature", "creature_a_1"), ("hero", "hero_a")},
        )

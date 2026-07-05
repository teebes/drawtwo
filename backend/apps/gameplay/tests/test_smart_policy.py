from django.test import TestCase

from apps.builder.schemas import DamageAction, DeckScript, HeroPower, Taunt
from apps.gameplay.agents.legal import list_legal_commands
from apps.gameplay.agents.policies import policy_for_script
from apps.gameplay.agents.policies.scripted import ScriptedPolicy
from apps.gameplay.agents.policies.smart import SmartPolicy, evaluate_state
from apps.gameplay.schemas.commands import (
    AttackCommand,
    EndTurnCommand,
    MulliganCommand,
    PlayCardCommand,
    UseHeroCommand,
)
from apps.gameplay.schemas.game import CardInPlay, Creature, GameState, HeroInPlay


def make_smart_test_state(**overrides) -> GameState:
    defaults = dict(
        turn=3,
        active="side_a",
        phase="main",
        cards={},
        creatures={},
        board={"side_a": [], "side_b": []},
        heroes={
            "side_a": HeroInPlay(
                hero_id="hero_a",
                template_slug="hero-a",
                name="Hero A",
                health=30,
                hero_power=HeroPower(name="None", actions=[]),
                exhausted=True,
            ),
            "side_b": HeroInPlay(
                hero_id="hero_b",
                template_slug="hero-b",
                name="Hero B",
                health=30,
                hero_power=HeroPower(name="None", actions=[]),
                exhausted=True,
            ),
        },
        hands={"side_a": [], "side_b": []},
        decks={"side_a": [], "side_b": []},
        graveyard={"side_a": [], "side_b": []},
        mana_pool={"side_a": 5, "side_b": 5},
        mana_used={"side_a": 0, "side_b": 0},
        mulligan_done={"side_a": True, "side_b": True},
    )
    defaults.update(overrides)
    return GameState(**defaults)


def add_creature(
    state: GameState,
    side: str,
    creature_id: str,
    attack: int,
    health: int,
    *,
    exhausted: bool = False,
    traits=None,
) -> None:
    card_id = f"card_{creature_id}"
    state.cards[card_id] = CardInPlay(
        card_id=card_id,
        card_type="creature",
        template_slug=creature_id,
        name=creature_id,
        attack=attack,
        health=health,
        cost=1,
        traits=traits or [],
    )
    state.creatures[creature_id] = Creature(
        creature_id=creature_id,
        card_id=card_id,
        name=creature_id,
        attack=attack,
        health=health,
        exhausted=exhausted,
        traits=traits or [],
    )
    state.board[side].append(creature_id)


class PolicyFactoryTests(TestCase):
    def test_smart_strategy_returns_smart_policy(self):
        policy = policy_for_script(DeckScript(strategy="smart"))
        self.assertIsInstance(policy, SmartPolicy)

    def test_other_strategies_return_scripted_policy(self):
        for strategy in ("rush", "control", "combo", "aggressive", "defensive"):
            policy = policy_for_script(DeckScript(strategy=strategy))
            self.assertIsInstance(policy, ScriptedPolicy)


class SmartPolicyTests(TestCase):
    def select(self, state: GameState, side: str = "side_a"):
        policy = SmartPolicy(DeckScript(strategy="smart"))
        return policy.select_command(state, list_legal_commands(state, side))

    def test_takes_lethal_on_hero_over_trade(self):
        state = make_smart_test_state()
        state.heroes["side_b"].health = 2
        add_creature(state, "side_a", "attacker", attack=2, health=2)
        add_creature(state, "side_b", "blocker", attack=1, health=1)

        command = self.select(state)

        self.assertIsInstance(command, AttackCommand)
        self.assertEqual(command.target_type, "hero")
        self.assertEqual(command.target_id, "hero_b")

    def test_plays_affordable_creature_from_hand(self):
        state = make_smart_test_state()
        state.cards["hand_1"] = CardInPlay(
            card_id="hand_1",
            card_type="creature",
            template_slug="grunt",
            name="Grunt",
            attack=3,
            health=3,
            cost=3,
        )
        state.hands["side_a"] = ["hand_1"]

        command = self.select(state)

        self.assertIsInstance(command, PlayCardCommand)
        self.assertEqual(command.card_id, "hand_1")

    def test_ends_turn_instead_of_suicidal_attack_into_taunt(self):
        state = make_smart_test_state()
        add_creature(state, "side_a", "small", attack=1, health=1)
        add_creature(
            state,
            "side_b",
            "wall",
            attack=9,
            health=9,
            traits=[Taunt()],
        )

        command = self.select(state)

        self.assertIsInstance(command, EndTurnCommand)

    def test_takes_favorable_trade_that_kills_threat(self):
        state = make_smart_test_state()
        add_creature(state, "side_a", "trader", attack=4, health=6)
        add_creature(
            state,
            "side_b",
            "threat",
            attack=4,
            health=4,
            traits=[Taunt()],
        )

        command = self.select(state)

        self.assertIsInstance(command, AttackCommand)
        self.assertEqual(command.target_type, "creature")
        self.assertEqual(command.target_id, "threat")

    def test_hero_power_kills_high_value_creature(self):
        state = make_smart_test_state()
        state.heroes["side_a"].exhausted = False
        state.heroes["side_a"].hero_power = HeroPower(
            name="Ping",
            actions=[DamageAction(amount=1, target="enemy")],
        )
        add_creature(state, "side_b", "glass_cannon", attack=6, health=1)

        command = self.select(state)

        self.assertIsInstance(command, UseHeroCommand)
        self.assertEqual(command.target_type, "creature")
        self.assertEqual(command.target_id, "glass_cannon")

    def test_mulligan_tosses_expensive_cards(self):
        state = make_smart_test_state(phase="mulligan")
        state.mulligan_done = {"side_a": False, "side_b": True}
        for card_id, cost in (("m_cheap", 1), ("m_mid", 3), ("m_big", 6)):
            state.cards[card_id] = CardInPlay(
                card_id=card_id,
                card_type="creature",
                template_slug=card_id,
                name=card_id,
                attack=2,
                health=2,
                cost=cost,
            )
        state.hands["side_a"] = ["m_cheap", "m_mid", "m_big"]
        state.mulligan_options["side_a"] = ["m_cheap", "m_mid", "m_big"]

        command = self.select(state)

        self.assertIsInstance(command, MulliganCommand)
        self.assertEqual(set(command.card_ids), {"m_big"})

    def test_no_pointless_moves_with_empty_position(self):
        state = make_smart_test_state()

        command = self.select(state)

        self.assertIsInstance(command, EndTurnCommand)

    def test_evaluate_state_prefers_winning_states(self):
        state = make_smart_test_state()
        neutral = evaluate_state(state, "side_a")

        won = state.model_copy(deep=True)
        won.winner = "side_a"
        lost = state.model_copy(deep=True)
        lost.winner = "side_b"

        self.assertGreater(evaluate_state(won, "side_a"), neutral)
        self.assertLess(evaluate_state(lost, "side_a"), neutral)

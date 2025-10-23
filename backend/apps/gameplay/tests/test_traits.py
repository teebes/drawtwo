"""
Tests for trait processing and effects.
"""
from apps.builder.schemas import (
    Battlecry,
    Charge,
    DamageAction,
    DrawAction,
    DeathRattle,
)
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.engine.handlers import spawn_creature
from apps.gameplay.schemas.engine import Success
from apps.gameplay.schemas.effects import PlayEffect, DrawEffect
from apps.gameplay.schemas.events import (
    CreatureDeathEvent,
    EndTurnEvent,
    PlayEvent,
)
from apps.gameplay.schemas.game import CardInPlay, Creature
from apps.gameplay.tests import GamePlayTestBase
from apps.gameplay import traits


class TestTraits(GamePlayTestBase):
    """Basic trait tests."""

    def test_battlecry_draw(self):
        battlecry_draw = CardInPlay(
            card_type="creature",
            card_id="1",
            template_slug="battlecry-draw",
            name="Battlecry Draw",
            description="Battlecry: Draw a card.",
            attack=1,
            health=1,
            cost=1,
            traits=[
                Battlecry(
                    type="battlecry",
                    actions=[
                        DrawAction()
                    ],
                )
            ],
        )

        self.game_state.cards["1"] = battlecry_draw
        self.game_state.hands["side_a"] = ["1"]
        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0

        # First, resolve the play effect
        play_effect = PlayEffect(
            side="side_a",
            source_id="1",
            position=0,
        )

        result = resolve(play_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # Card is on the board
        self.assertEqual(new_state.board["side_a"], ["1"])
        # PlayEvent is generated
        self.assertEqual(result.events[0].type, 'event_play')

        # Now process the PlayEvent through the trait system to trigger battlecry
        play_event = result.events[0]
        trait_result = traits.apply(new_state, play_event)

        # The DrawAction should create a DrawEffect as a child effect
        self.assertEqual(len(trait_result.child_effects), 1)
        self.assertEqual(trait_result.child_effects[0].type, 'effect_draw')
        self.assertEqual(trait_result.child_effects[0].side, 'side_a')


class TestTraitProcessing(GamePlayTestBase):
    """Tests for the event-driven trait processing system."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        # Add test cards with traits
        self.game_state.cards["card_1"] = CardInPlay(
            card_type="creature",
            card_id="card_1",
            template_slug="test-card",
            name="Test Card",
            attack=2,
            health=3,
            cost=2,
            traits=[Charge()],
            exhausted=True
        )
        self.game_state.cards["card_2"] = CardInPlay(
            card_type="creature",
            card_id="card_2",
            template_slug="battlecry-card",
            name="Battlecry Card",
            attack=1,
            health=2,
            cost=1,
            traits=[Battlecry(actions=[DrawAction(amount=2)])],
            exhausted=True
        )

    def test_no_trait_triggers(self):
        """Test that non-triggering events don't generate effects."""
        # Create an event that doesn't trigger any traits
        end_turn_event = EndTurnEvent(side="side_a")

        # Apply traits
        result = traits.apply(self.game_state, end_turn_event)

        # Should not generate any effects
        self.assertEqual(len(result.child_effects), 0)
        self.assertEqual(len(result.events), 0)

    def test_trait_on_card_without_traits(self):
        """Test that cards without traits don't cause issues."""
        # Create a card without traits
        self.game_state.cards["card_3"] = CardInPlay(
            card_type="creature",
            card_id="card_3",
            template_slug="plain-card",
            name="Plain Card",
            attack=1,
            health=1,
            cost=1,
            traits=[],
            exhausted=True
        )

        play_event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="card_3",
            position=0
        )

        # Apply traits
        result = traits.apply(self.game_state, play_event)

        # Should not generate any effects
        self.assertEqual(len(result.child_effects), 0)

    def test_charge_trait(self):
        """Test that charge trait sets exhausted to False on play."""

        creature = spawn_creature(
            card=self.game_state.cards["card_1"],
            state=self.game_state,
            side="side_a",
        )

        # Create a play event for a card with charge
        play_event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="card_1",
            position=0,
            creature_id=creature.creature_id,
        )

        # Creature starts out exhausted
        self.assertTrue(creature.exhausted)
        # Apply traits
        result = traits.apply(self.game_state, play_event)

        # Creature should no longer be exhausted
        new_state = result.new_state
        creature = new_state.creatures[creature.creature_id]
        self.assertFalse(creature.exhausted)
        self.assertEqual(len(result.child_effects), 0)

    def test_damage_battlecry(self):
        self.game_state.board["side_b"] = ["card_1"]
        self.assertEqual(self.game_state.cards["card_1"].health, 3)

        battlecry_damage = CardInPlay(
            card_type="creature",
            card_id="card_3",
            template_slug="battlecry-damage",
            name="Battlecry Damage",
            description="Battlecry: Deal 1 damage to a target.",
            attack=1,
            health=1,
            cost=1,
            traits=[Battlecry(actions=[DamageAction(amount=1, target="enemy")])],
            exhausted=False,
        )
        self.game_state.cards["card_3"] = battlecry_damage
        self.game_state.hands["side_a"] = ["card_3"]
        event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="card_3",
            position=0,
            target_type="creature",
            target_id="card_1",
        )
        result = traits.apply(self.game_state, event)
        self.assertTrue(isinstance(result, Success))
        self.assertEqual(result.child_effects[0].type, "effect_damage")
        self.assertEqual(result.child_effects[0].side, "side_a")
        self.assertEqual(result.child_effects[0].source_type, "card")
        self.assertEqual(result.child_effects[0].source_id, "card_3")
        self.assertEqual(result.child_effects[0].target_type, "creature")
        self.assertEqual(result.child_effects[0].target_id, "card_1")
        self.assertEqual(result.child_effects[0].damage, 1)
        self.assertEqual(result.child_effects[0].retaliate, False)

    def test_battlecry_draw(self):

        creature = spawn_creature(
            card=self.game_state.cards["card_2"],
            state=self.game_state,
            side="side_a",
        )

        # Create a play event for a card with battlecry
        play_event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="card_2",
            position=0,
            creature_id=creature.creature_id,
        )

        # Apply traits
        result = traits.apply(self.game_state, play_event)

        # Should generate a DrawEffect
        self.assertEqual(len(result.child_effects), 1)
        self.assertIsInstance(result.child_effects[0], DrawEffect)
        self.assertEqual(result.child_effects[0].amount, 2)
        self.assertEqual(result.child_effects[0].side, "side_a")

    def test_deathrattle_draw(self):
        killer_card = CardInPlay(
            card_type="creature",
            card_id="card_4",
            template_slug="killer-card",
            name="Killer Card",
            attack=1,
            health=1,
            cost=1,
            traits=[],
        )
        killer_creature = spawn_creature(
            card=killer_card,
            state=self.game_state,
            side="side_a",
        )

        rattling_card = CardInPlay(
            card_type="creature",
            card_id="card_3",
            template_slug="rattling-card",
            name="Rattling Card",
            attack=1,
            health=1,
            cost=1,
            traits=[DeathRattle(actions=[DrawAction()])],
        )
        rattling_creature = spawn_creature(
            card=rattling_card,
            state=self.game_state,
            side="side_b",
        )

        self.assertEqual(self.game_state.board["side_a"][0], "1")
        self.assertEqual(self.game_state.board["side_b"][0], "2")

        # event if killer_creature kills rattling_creature
        death_event = CreatureDeathEvent(
            side="side_b",
            creature=rattling_creature,
            source_type="creature",
            source_id="1",
            target_type="creature",
            target_id="2",
        )
        result = traits.apply(self.game_state, death_event)
        self.assertEqual(len(result.child_effects), 1)
        self.assertIsInstance(result.child_effects[0], DrawEffect)
        self.assertEqual(result.child_effects[0].side, "side_b")
        self.assertEqual(result.child_effects[0].amount, 1)
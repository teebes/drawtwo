"""
Tests for the Clear action (removes all creatures from board without triggering deathrattle).
"""
from apps.builder.schemas import Battlecry, ClearAction, DeathRattle, DrawAction
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.engine.handlers import spawn_creature
from apps.gameplay.schemas.effects import ClearEffect
from apps.gameplay.schemas.events import ClearEvent, CreatureDeathEvent
from apps.gameplay.schemas.game import CardInPlay, Creature
from apps.gameplay.schemas.engine import Success
from apps.gameplay.tests import GamePlayTestBase
from apps.gameplay.schemas.events import PlayEvent
from apps.gameplay import traits


class TestClearAction(GamePlayTestBase):
    """Tests for the Clear action (removes all creatures from board without triggering deathrattle)."""

    def test_clear_both_sides(self):
        """Test that clear action with target='both' removes all creatures from both sides."""
        # Create creatures on both sides
        for i in range(2):
            creature_card = CardInPlay(
                card_type="creature",
                card_id=f"creature_a_{i}",
                template_slug=f"creature-a-{i}",
                name=f"Creature A {i}",
                attack=1,
                health=1,
                cost=1,
                traits=[],
            )
            spawn_creature(
                card=creature_card,
                state=self.game_state,
                side="side_a",
            )

        for i in range(3):
            creature_card = CardInPlay(
                card_type="creature",
                card_id=f"creature_b_{i}",
                template_slug=f"creature-b-{i}",
                name=f"Creature B {i}",
                attack=1,
                health=1,
                cost=1,
                traits=[],
            )
            spawn_creature(
                card=creature_card,
                state=self.game_state,
                side="side_b",
            )

        # Verify creatures are on board
        self.assertEqual(len(self.game_state.board["side_a"]), 2)
        self.assertEqual(len(self.game_state.board["side_b"]), 3)

        # Create clear effect targeting both sides
        clear_effect = ClearEffect(
            side="side_a",
            source_type="card",
            source_id="clear_spell",
            target="both",
        )

        # Resolve the clear effect
        result = resolve(clear_effect, self.game_state)
        self.assertIsInstance(result, Success)

        # Verify all creatures were removed from both sides
        self.assertEqual(len(result.new_state.board["side_a"]), 0)
        self.assertEqual(len(result.new_state.board["side_b"]), 0)

        # Verify ClearEvent was emitted
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, "event_clear")
        self.assertIsInstance(result.events[0], ClearEvent)
        self.assertEqual(result.events[0].target, "both")

        # Verify no child effects
        self.assertEqual(len(result.child_effects), 0)

    def test_clear_opponent_side_only(self):
        """Test that clear action with target='opponent' removes only opponent's creatures."""
        # Create creatures on both sides
        for i in range(2):
            creature_card = CardInPlay(
                card_type="creature",
                card_id=f"creature_a_{i}",
                template_slug=f"creature-a-{i}",
                name=f"Creature A {i}",
                attack=1,
                health=1,
                cost=1,
                traits=[],
            )
            spawn_creature(
                card=creature_card,
                state=self.game_state,
                side="side_a",
            )

        for i in range(3):
            creature_card = CardInPlay(
                card_type="creature",
                card_id=f"creature_b_{i}",
                template_slug=f"creature-b-{i}",
                name=f"Creature B {i}",
                attack=1,
                health=1,
                cost=1,
                traits=[],
            )
            spawn_creature(
                card=creature_card,
                state=self.game_state,
                side="side_b",
            )

        # Verify creatures are on board
        self.assertEqual(len(self.game_state.board["side_a"]), 2)
        self.assertEqual(len(self.game_state.board["side_b"]), 3)

        # Create clear effect targeting opponent only
        clear_effect = ClearEffect(
            side="side_a",
            source_type="card",
            source_id="clear_spell",
            target="opponent",
        )

        # Resolve the clear effect
        result = resolve(clear_effect, self.game_state)
        self.assertIsInstance(result, Success)

        # Verify only opponent's creatures were removed
        self.assertEqual(len(result.new_state.board["side_a"]), 2)  # Own creatures remain
        self.assertEqual(len(result.new_state.board["side_b"]), 0)  # Opponent's creatures removed

        # Verify ClearEvent was emitted
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, "event_clear")
        self.assertIsInstance(result.events[0], ClearEvent)
        self.assertEqual(result.events[0].target, "opponent")

    def test_clear_own_side_only(self):
        """Test that clear action with target='own' removes only own creatures."""
        # Create creatures on both sides
        for i in range(2):
            creature_card = CardInPlay(
                card_type="creature",
                card_id=f"creature_a_{i}",
                template_slug=f"creature-a-{i}",
                name=f"Creature A {i}",
                attack=1,
                health=1,
                cost=1,
                traits=[],
            )
            spawn_creature(
                card=creature_card,
                state=self.game_state,
                side="side_a",
            )

        for i in range(3):
            creature_card = CardInPlay(
                card_type="creature",
                card_id=f"creature_b_{i}",
                template_slug=f"creature-b-{i}",
                name=f"Creature B {i}",
                attack=1,
                health=1,
                cost=1,
                traits=[],
            )
            spawn_creature(
                card=creature_card,
                state=self.game_state,
                side="side_b",
            )

        # Verify creatures are on board
        self.assertEqual(len(self.game_state.board["side_a"]), 2)
        self.assertEqual(len(self.game_state.board["side_b"]), 3)

        # Create clear effect targeting own side only
        clear_effect = ClearEffect(
            side="side_a",
            source_type="card",
            source_id="clear_spell",
            target="own",
        )

        # Resolve the clear effect
        result = resolve(clear_effect, self.game_state)
        self.assertIsInstance(result, Success)

        # Verify only own creatures were removed
        self.assertEqual(len(result.new_state.board["side_a"]), 0)  # Own creatures removed
        self.assertEqual(len(result.new_state.board["side_b"]), 3)  # Opponent's creatures remain

        # Verify ClearEvent was emitted
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, "event_clear")
        self.assertIsInstance(result.events[0], ClearEvent)
        self.assertEqual(result.events[0].target, "own")

    def test_clear_does_not_trigger_deathrattle(self):
        """Test that clear does NOT trigger deathrattle effects."""
        # Create creatures with deathrattle on both sides
        deathrattle_card_a = CardInPlay(
            card_type="creature",
            card_id="rattling_a",
            template_slug="rattling-a",
            name="Rattling A",
            attack=1,
            health=1,
            cost=1,
            traits=[DeathRattle(actions=[DrawAction(amount=1)])],
        )
        spawn_creature(
            card=deathrattle_card_a,
            state=self.game_state,
            side="side_a",
        )

        deathrattle_card_b = CardInPlay(
            card_type="creature",
            card_id="rattling_b",
            template_slug="rattling-b",
            name="Rattling B",
            attack=1,
            health=1,
            cost=1,
            traits=[DeathRattle(actions=[DrawAction(amount=1)])],
        )
        spawn_creature(
            card=deathrattle_card_b,
            state=self.game_state,
            side="side_b",
        )

        # Verify creatures are on board
        self.assertEqual(len(self.game_state.board["side_a"]), 1)
        self.assertEqual(len(self.game_state.board["side_b"]), 1)

        # Create clear effect targeting both sides
        clear_effect = ClearEffect(
            side="side_a",
            source_type="card",
            source_id="clear_spell",
            target="both",
        )

        # Resolve the clear effect
        result = resolve(clear_effect, self.game_state)
        self.assertIsInstance(result, Success)

        # Verify creatures were removed
        self.assertEqual(len(result.new_state.board["side_a"]), 0)
        self.assertEqual(len(result.new_state.board["side_b"]), 0)

        # Verify ClearEvent was emitted (not CreatureDeathEvent)
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, "event_clear")
        self.assertNotIsInstance(result.events[0], CreatureDeathEvent)

        # Verify no child effects (deathrattle should NOT trigger)
        self.assertEqual(len(result.child_effects), 0)

    def test_clear_action_via_battlecry(self):
        """Test that clear action works when triggered via battlecry."""
        # Create creatures on opponent's side
        for i in range(2):
            creature_card = CardInPlay(
                card_type="creature",
                card_id=f"creature_b_{i}",
                template_slug=f"creature-b-{i}",
                name=f"Creature B {i}",
                attack=1,
                health=1,
                cost=1,
                traits=[],
            )
            spawn_creature(
                card=creature_card,
                state=self.game_state,
                side="side_b",
            )

        # Verify creatures are on board
        self.assertEqual(len(self.game_state.board["side_b"]), 2)

        # Create battlecry card with clear action
        clear_card = CardInPlay(
            card_type="spell",
            card_id="clear_spell",
            template_slug="clear-spell",
            name="Clear Spell",
            cost=5,
            traits=[Battlecry(actions=[ClearAction(target="opponent")])],
        )
        self.game_state.cards["clear_spell"] = clear_card

        # Create play event
        play_event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="clear_spell",
            position=0,
        )

        # Process battlecry
        result = traits.apply(self.game_state, play_event)
        self.assertEqual(len(result.child_effects), 1)
        self.assertIsInstance(result.child_effects[0], ClearEffect)
        self.assertEqual(result.child_effects[0].target, "opponent")

        # Resolve the clear effect
        clear_result = resolve(result.child_effects[0], self.game_state)
        self.assertIsInstance(clear_result, Success)

        # Verify opponent's creatures were removed
        self.assertEqual(len(clear_result.new_state.board["side_b"]), 0)

    def test_clear_empty_board(self):
        """Test that clear action works on empty boards without errors."""
        # Verify boards are empty
        self.assertEqual(len(self.game_state.board["side_a"]), 0)
        self.assertEqual(len(self.game_state.board["side_b"]), 0)

        # Create clear effect targeting both sides
        clear_effect = ClearEffect(
            side="side_a",
            source_type="card",
            source_id="clear_spell",
            target="both",
        )

        # Resolve the clear effect - should succeed even with empty boards
        result = resolve(clear_effect, self.game_state)
        self.assertIsInstance(result, Success)

        # Verify boards are still empty
        self.assertEqual(len(result.new_state.board["side_a"]), 0)
        self.assertEqual(len(result.new_state.board["side_b"]), 0)

        # Verify ClearEvent was still emitted
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, "event_clear")


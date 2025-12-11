"""
Tests for summon effect functionality.
"""
from apps.builder.schemas import Battlecry, SummonAction
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.schemas.engine import Success, Rejected
from apps.gameplay.schemas.effects import SummonEffect
from apps.gameplay.schemas.events import SummonEvent
from apps.gameplay.schemas.game import CardInPlay
from apps.gameplay.tests import GamePlayTestBase


class SummonEffectTests(GamePlayTestBase):
    """Tests for the summon effect handler."""

    def setUp(self):
        super().setUp()
        # Add a summonable card template to the game state
        egg_template = CardInPlay(
            card_type="creature",
            card_id="",  # Placeholder for template
            template_slug="egg",
            name="Egg",
            description="A small egg",
            attack=0,
            health=1,
            cost=0,
        )
        self.game_state.summonable_cards["egg"] = egg_template

    def test_summon_creature_success(self):
        """Test successfully summoning a creature."""
        # Create a source card that will summon
        source_card = CardInPlay(
            card_type="creature",
            card_id="1",
            template_slug="chicken",
            name="Chicken",
            attack=1,
            health=1,
            cost=1,
        )
        self.game_state.cards["1"] = source_card

        effect = SummonEffect(
            side="side_a",
            source_type="card",
            source_id="1",
            target="egg",
        )

        result = resolve(effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # Check that a new card was created
        self.assertIn("2", new_state.cards)  # card_id should be 2 (1 was the source)
        summoned_card = new_state.cards["2"]
        self.assertEqual(summoned_card.template_slug, "egg")
        self.assertEqual(summoned_card.name, "Egg")
        self.assertEqual(summoned_card.attack, 0)
        self.assertEqual(summoned_card.health, 1)

        # Check that a creature was spawned on the board
        self.assertEqual(len(new_state.board["side_a"]), 1)
        creature_id = new_state.board["side_a"][0]
        self.assertIn(creature_id, new_state.creatures)
        creature = new_state.creatures[creature_id]
        self.assertEqual(creature.card_id, "2")
        self.assertEqual(creature.name, "Egg")
        self.assertTrue(creature.exhausted)  # Newly summoned creatures are exhausted

        # Check that a SummonEvent was emitted
        self.assertEqual(len(result.events), 1)
        event = result.events[0]
        self.assertIsInstance(event, SummonEvent)
        self.assertEqual(event.type, "event_summon")
        self.assertEqual(event.side, "side_a")
        self.assertEqual(event.source_type, "card")
        self.assertEqual(event.source_id, "1")
        self.assertEqual(event.target_type, "card")
        self.assertEqual(event.target_id, "2")

    def test_summon_creature_to_correct_side(self):
        """Test that summoned creatures go to the correct side."""
        source_card = CardInPlay(
            card_type="creature",
            card_id="1",
            template_slug="chicken",
            name="Chicken",
            attack=1,
            health=1,
            cost=1,
        )
        self.game_state.cards["1"] = source_card

        # Summon to side_b
        effect = SummonEffect(
            side="side_b",
            source_type="card",
            source_id="1",
            target="egg",
        )

        result = resolve(effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # Creature should be on side_b, not side_a
        self.assertEqual(len(new_state.board["side_a"]), 0)
        self.assertEqual(len(new_state.board["side_b"]), 1)
        creature_id = new_state.board["side_b"][0]
        self.assertIn(creature_id, new_state.creatures)

    def test_summon_card_not_found(self):
        """Test that summoning a non-existent card is rejected."""
        source_card = CardInPlay(
            card_type="creature",
            card_id="1",
            template_slug="chicken",
            name="Chicken",
            attack=1,
            health=1,
            cost=1,
        )
        self.game_state.cards["1"] = source_card

        effect = SummonEffect(
            side="side_a",
            source_type="card",
            source_id="1",
            target="nonexistent-card",
        )

        result = resolve(effect, self.game_state)
        self.assertTrue(isinstance(result, Rejected))
        self.assertIn("not found in summonable cards", result.reason)

        # No card should be created
        self.assertNotIn("2", self.game_state.cards)
        self.assertEqual(len(self.game_state.board["side_a"]), 0)

    def test_summon_non_creature_rejected(self):
        """Test that summoning a spell card is rejected."""
        # Add a spell to summonable cards
        spell_template = CardInPlay(
            card_type="spell",
            card_id="",  # Placeholder for template
            template_slug="fireball",
            name="Fireball",
            description="A fireball spell",
            cost=3,
        )
        self.game_state.summonable_cards["fireball"] = spell_template

        source_card = CardInPlay(
            card_type="creature",
            card_id="1",
            template_slug="wizard",
            name="Wizard",
            attack=1,
            health=1,
            cost=1,
        )
        self.game_state.cards["1"] = source_card

        effect = SummonEffect(
            side="side_a",
            source_type="card",
            source_id="1",
            target="fireball",
        )

        result = resolve(effect, self.game_state)
        self.assertTrue(isinstance(result, Rejected))
        self.assertIn("Cannot summon non-creature card", result.reason)

        # No card should be created
        self.assertNotIn("2", self.game_state.cards)
        self.assertEqual(len(self.game_state.board["side_a"]), 0)

    def test_summon_multiple_creatures_unique_ids(self):
        """Test that multiple summons create unique card IDs."""
        source_card = CardInPlay(
            card_type="creature",
            card_id="1",
            template_slug="chicken",
            name="Chicken",
            attack=1,
            health=1,
            cost=1,
        )
        self.game_state.cards["1"] = source_card

        # First summon
        effect1 = SummonEffect(
            side="side_a",
            source_type="card",
            source_id="1",
            target="egg",
        )
        result1 = resolve(effect1, self.game_state)
        self.assertTrue(isinstance(result1, Success))
        new_state1 = result1.new_state

        # Second summon
        effect2 = SummonEffect(
            side="side_a",
            source_type="card",
            source_id="1",
            target="egg",
        )
        result2 = resolve(effect2, new_state1)
        self.assertTrue(isinstance(result2, Success))
        new_state2 = result2.new_state

        # Both cards should exist with different IDs
        self.assertIn("2", new_state2.cards)
        self.assertIn("3", new_state2.cards)
        self.assertEqual(new_state2.cards["2"].template_slug, "egg")
        self.assertEqual(new_state2.cards["3"].template_slug, "egg")

        # Both creatures should be on the board
        self.assertEqual(len(new_state2.board["side_a"]), 2)
        self.assertEqual(len(new_state2.creatures), 2)

    def test_summon_creature_preserves_template_data(self):
        """Test that summoned creatures preserve all template data."""
        # Create a more complex template
        complex_template = CardInPlay(
            card_type="creature",
            card_id="",
            template_slug="dragon",
            name="Dragon",
            description="A mighty dragon",
            attack=5,
            health=8,
            cost=6,
            traits=[Battlecry(actions=[])],
        )
        self.game_state.summonable_cards["dragon"] = complex_template

        source_card = CardInPlay(
            card_type="creature",
            card_id="1",
            template_slug="summoner",
            name="Summoner",
            attack=1,
            health=1,
            cost=1,
        )
        self.game_state.cards["1"] = source_card

        effect = SummonEffect(
            side="side_a",
            source_type="card",
            source_id="1",
            target="dragon",
        )

        result = resolve(effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        summoned_card = new_state.cards["2"]
        self.assertEqual(summoned_card.name, "Dragon")
        self.assertEqual(summoned_card.description, "A mighty dragon")
        self.assertEqual(summoned_card.attack, 5)
        self.assertEqual(summoned_card.health, 8)
        self.assertEqual(summoned_card.cost, 6)
        self.assertEqual(len(summoned_card.traits), 1)
        self.assertEqual(summoned_card.traits[0].type, "battlecry")

"""
Tests for game ending conditions.
"""
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.schemas.engine import Success
from apps.gameplay.schemas.effects import DrawEffect, DamageEffect
from apps.gameplay.tests import GamePlayTestBase


class TestEndGame(GamePlayTestBase):
    """Tests for game ending conditions."""

    def test_decking_out_via_card_action(self):
        # Ensure the deck is empty
        self.game_state.decks["side_a"] = []

        draw_effect = DrawEffect(
            side="side_a",
            amount=1,
        )
        result = resolve(draw_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        # When deck is empty, a GameOverEvent is generated
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, 'event_game_over')
        # The opposing side wins
        self.assertEqual(result.events[0].winner, 'side_b')

    def test_hero_death_by_damage(self):
        damage_effect = DamageEffect(
            side="side_a",
            damage_type="physical",
            source_type="hero",
            source_id="1",
            target_type="hero",
            target_id="2",
            damage=10,
        )

        result = resolve(damage_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state
        self.assertEqual(result.events[0].type, 'event_damage')
        self.assertEqual(result.events[1].type, 'event_game_over')
        self.assertEqual(result.events[1].winner, 'side_a')

"""
Tests for game ending conditions.
"""

from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.schemas.effects import DamageEffect, DrawEffect
from apps.gameplay.schemas.engine import Success
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
        self.assertEqual(result.events[0].type, "event_game_over")
        # The opposing side wins
        self.assertEqual(result.events[0].winner, "side_b")
        self.assertEqual(result.events[0].reason, "empty_deck")

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
        self.assertEqual(result.events[0].type, "event_damage")
        self.assertEqual(result.events[1].type, "event_game_over")
        self.assertEqual(result.events[1].winner, "side_a")
        self.assertIsNone(result.events[1].reason)

    def test_lethal_hero_damage_awards_opponent_of_target(self):
        for source_side in ("side_a", "side_b"):
            for target_side in ("side_a", "side_b"):
                for damage in (10, 11):
                    with self.subTest(
                        source=source_side, target=target_side, damage=damage
                    ):
                        effect = DamageEffect(
                            side=source_side,
                            source_type="hero",
                            source_id=self.game_state.heroes[source_side].hero_id,
                            target_type="hero",
                            target_id=self.game_state.heroes[target_side].hero_id,
                            damage=damage,
                            damage_type="spell",
                        )

                        result = resolve(effect, self.game_state)

                        winner = "side_b" if target_side == "side_a" else "side_a"
                        self.assertIsInstance(result, Success)
                        self.assertEqual(result.new_state.winner, winner)
                        self.assertEqual(result.events[0].target_side, target_side)
                        self.assertEqual(result.events[1].type, "event_game_over")
                        self.assertEqual(result.events[1].winner, winner)
                        self.assertEqual(result.events[1].side, source_side)

    def test_nonlethal_self_damage_does_not_end_game(self):
        effect = DamageEffect(
            side="side_a",
            source_type="hero",
            source_id="1",
            target_type="hero",
            target_id="1",
            damage=1,
            damage_type="spell",
        )

        result = resolve(effect, self.game_state)

        self.assertIsInstance(result, Success)
        self.assertEqual(result.new_state.heroes["side_a"].health, 9)
        self.assertEqual(result.new_state.winner, "none")
        self.assertEqual([event.type for event in result.events], ["event_damage"])

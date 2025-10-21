"""
Tests for game engine effect resolution.
"""
from apps.builder.schemas import Battlecry, DamageAction, Charge
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.schemas.engine import Success, Prevented, Rejected
from apps.gameplay.schemas.effects import (
    StartGameEffect,
    PlayEffect,
    UseHeroEffect,
)
from apps.gameplay.schemas.game import CardInPlay, Creature
from apps.gameplay.tests import GamePlayTestBase
from apps.gameplay import traits


class EngineTests(GamePlayTestBase):
    """Tests effect resolution by the game engine."""

    def test_start_game_effect(self):
        effect = StartGameEffect(side='side_a')
        result = resolve(effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        self.assertEqual(len(result.child_effects), 7)
        self.assertEqual(result.child_effects[0].type, 'effect_draw')
        self.assertEqual(result.child_effects[0].side, 'side_a')
        self.assertEqual(result.child_effects[1].type, 'effect_draw')
        self.assertEqual(result.child_effects[1].side, 'side_a')
        self.assertEqual(result.child_effects[2].type, 'effect_draw')
        self.assertEqual(result.child_effects[2].side, 'side_a')
        self.assertEqual(result.child_effects[3].type, 'effect_draw')
        self.assertEqual(result.child_effects[3].side, 'side_b')
        self.assertEqual(result.child_effects[4].type, 'effect_draw')
        self.assertEqual(result.child_effects[4].side, 'side_b')
        self.assertEqual(result.child_effects[5].type, 'effect_draw')
        self.assertEqual(result.child_effects[5].side, 'side_b')
        self.assertEqual(result.child_effects[6].type, 'effect_phase')

    def test_play_creature_card_to_board(self):
        creature = CardInPlay(
            card_type="creature",
            card_id="1",
            template_slug="test",
            name="test",
            attack=1,
            health=1,
            cost=1,
            exhausted=False,
        )
        self.game_state.cards["1"] = creature
        self.game_state.hands["side_a"] = ["1"]
        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0

        effect = PlayEffect(
            side="side_a",
            source_id="1",
            position=0,
        )
        result = resolve(effect, self.game_state)
        new_state = result.new_state
        self.assertEqual(new_state.board["side_a"], ["1"])

    def test_use_hero_power_on_hero(self):
        effect = UseHeroEffect(
            side="side_a",
            source_id="1",  # Use the actual hero_id from the game state
            target_type="hero",
            target_id="2",
        )

        # Hero power can't be used if the hero is exhausted
        self.assertTrue(self.game_state.heroes["side_a"].exhausted)
        result = resolve(effect, self.game_state)
        self.assertTrue(isinstance(result, Rejected))
        self.assertEqual(result.reason, "Hero is exhausted")

        # Hero power can be used if the hero is not exhausted
        self.game_state.heroes["side_a"].exhausted = False
        result = resolve(effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        self.assertEqual(len(result.child_effects), 2)
        self.assertEqual(result.child_effects[0].type, 'effect_damage')
        self.assertEqual(result.child_effects[1].type, 'effect_mark_exhausted')

    def test_play_spell_card(self):
        spell_card = CardInPlay(
            card_type="spell",
            card_id="1",
            template_slug="small-nuke",
            name="Small Nuke",
            cost=1,
            traits=[
                Battlecry(
                    actions=[
                        DamageAction(
                            amount=1,
                            target="enemy",
                        )
                    ]
                )
            ],
        )

        # Play can't afford the spell
        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 1
        self.game_state.cards["1"] = spell_card
        self.game_state.hands["side_a"] = ["1"]
        play_effect = PlayEffect(
            side="side_a",
            source_id="1",
            position=0,
            target_type="hero",
            target_id="2",
        )
        result = resolve(play_effect, self.game_state)
        self.assertTrue(isinstance(result, Rejected))
        self.assertIn("energy", result.reason.lower())

        # Play can afford the spell
        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0
        self.game_state.cards["1"] = spell_card
        self.game_state.hands["side_a"] = ["1"]

        play_effect = PlayEffect(
            side="side_a",
            source_id="1",
            position=0,
            target_type="hero",
            target_id="2",
        )
        result = resolve(play_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # PlayEffect generates a PlayEvent that triggers battlecry actions
        self.assertEqual(result.events[0].type, 'event_play')
        self.assertEqual(new_state.hands["side_a"], [])
        self.assertEqual(new_state.graveyard["side_a"], ["1"])
        self.assertEqual(new_state.mana_used["side_a"], 1)

    def test_play_spell_card_on_creature(self):
        spell_card = CardInPlay(
            card_type="spell",
            card_id="1",
            template_slug="small-nuke",
            name="Small Nuke",
            cost=1,
            traits=[
                Battlecry(
                    actions=[
                        DamageAction(
                            amount=1,
                            target="enemy",
                        )
                    ]
                )
            ],
        )

        # Create a creature on the board (not a card)
        creature = Creature(
            creature_id="2",
            card_id="creature_card_2",
            name="test",
            attack=1,
            health=10,
            exhausted=False,
        )

        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0
        self.game_state.cards["1"] = spell_card
        self.game_state.creatures["2"] = creature
        self.game_state.hands["side_a"] = ["1"]
        self.game_state.board["side_b"] = ["2"]

        play_effect = PlayEffect(
            side="side_a",
            source_id="1",
            position=0,
            target_type="creature",
            target_id="2",
        )
        result = resolve(play_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # PlayEffect generates a PlayEvent that triggers battlecry actions
        self.assertEqual(result.events[0].type, 'event_play')
        self.assertEqual(new_state.hands["side_a"], [])
        self.assertEqual(new_state.graveyard["side_a"], ["1"])
        self.assertEqual(new_state.mana_used["side_a"], 1)

        # Now process the PlayEvent through traits to trigger the battlecry
        play_event = result.events[0]
        trait_result = traits.apply(new_state, play_event)
        self.assertEqual(len(trait_result.child_effects), 1)
        self.assertEqual(trait_result.child_effects[0].type, 'effect_damage')

        # Actually resolve the DamageEffect that was generated by the battlecry
        damage_effect = trait_result.child_effects[0]
        damage_result = resolve(damage_effect, new_state)
        self.assertTrue(isinstance(damage_result, Success))
        # This should work without errors - creature should take 1 damage
        self.assertEqual(damage_result.new_state.creatures["2"].health, 9)

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
            attack_max=1,
            health=10,
            health_max=10,
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

    def test_play_spell_buff_requires_target(self):
        """Targeted buff spells should require an explicit target (no auto-leftmost)."""
        from apps.builder.schemas import Battlecry, BuffAction
        from apps.gameplay.schemas.game import CardInPlay, Creature

        spell_card = CardInPlay(
            card_type="spell",
            card_id="buff_spell_1",
            template_slug="boom",
            name="Boom",
            description="+1 attack +1 health to the targeted unit",
            cost=0,
            traits=[
                Battlecry(
                    actions=[
                        BuffAction(attribute="health", amount=1, target="creature", scope="single"),
                        BuffAction(attribute="attack", amount=1, target="creature", scope="single"),
                    ]
                )
            ],
        )

        # Two friendly creatures on board
        c1 = Creature(
            creature_id="c1",
            card_id="c1_card",
            name="c1",
            attack=1,
            attack_max=1,
            health=3,
            health_max=3,
            exhausted=False,
        )
        c2 = Creature(
            creature_id="c2",
            card_id="c2_card",
            name="c2",
            attack=2,
            attack_max=2,
            health=4,
            health_max=4,
            exhausted=False,
        )
        self.game_state.creatures["c1"] = c1
        self.game_state.creatures["c2"] = c2
        self.game_state.board["side_a"] = ["c1", "c2"]

        self.game_state.cards["buff_spell_1"] = spell_card
        self.game_state.hands["side_a"] = ["buff_spell_1"]
        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0

        # Missing target should be rejected
        play_effect_missing_target = PlayEffect(
            side="side_a",
            source_id="buff_spell_1",
            position=0,
        )
        result = resolve(play_effect_missing_target, self.game_state)
        self.assertTrue(isinstance(result, Rejected))
        self.assertIn("target", result.reason.lower())
        self.assertIn("buff_spell_1", self.game_state.hands["side_a"])

        # Providing target should succeed and buff the chosen creature
        play_effect = PlayEffect(
            side="side_a",
            source_id="buff_spell_1",
            position=0,
            target_type="creature",
            target_id="c2",
        )
        result = resolve(play_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state
        play_event = result.events[0]

        trait_result = traits.apply(new_state, play_event)
        self.assertEqual(len(trait_result.child_effects), 2)

        # Resolve both buff effects
        for eff in trait_result.child_effects:
            resolve_result = resolve(eff, new_state)
            self.assertTrue(isinstance(resolve_result, Success))
            new_state = resolve_result.new_state

        self.assertEqual(new_state.creatures["c1"].attack, 1)
        self.assertEqual(new_state.creatures["c1"].health, 3)
        self.assertEqual(new_state.creatures["c2"].attack, 3)
        self.assertEqual(new_state.creatures["c2"].health, 5)

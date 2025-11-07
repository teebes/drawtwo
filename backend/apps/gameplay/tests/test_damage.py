"""
Tests for damage effects and combat mechanics.
"""
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.schemas.engine import Success
from apps.gameplay.schemas.effects import DamageEffect
from apps.gameplay.schemas.game import Creature
from apps.gameplay.tests import GamePlayTestBase


class TestDamage(GamePlayTestBase):
    """Tests for damage effects."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.creature = Creature(
            creature_id="1",
            card_id="card_1",
            name="test",
            attack=1,
            attack_max=1,
            health=1,
            health_max=1,
            exhausted=False,
        )

    def test_creature_to_hero_damage(self):
        self.game_state.creatures["1"] = self.creature
        self.game_state.board['side_a'] = ["1"]
        damage_effect = DamageEffect(
            side="side_a",
            damage_type="physical",
            source_type="creature",
            source_id="1",
            target_type="hero",
            target_id="2",
            damage=1,
        )

        result = resolve(damage_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # The target hero's health went down
        self.assertEqual(new_state.heroes['side_b'].health, 9)

        # A DamageEvent is created for UI updates
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, 'event_damage')

    def test_creature_to_creature_damage(self):
        target_creature = Creature(
            creature_id="2",
            card_id="card_2",
            name="test",
            attack=2,
            attack_max=2,
            health=10,
            health_max=10,
            exhausted=False,
        )

        self.game_state.creatures["1"] = self.creature
        self.game_state.creatures["2"] = target_creature
        self.game_state.board['side_a'] = ["1"]
        self.game_state.board['side_b'] = ["2"]
        damage_effect = DamageEffect(
            side="side_a",
            damage_type="physical",
            source_type="creature",
            source_id="1",
            target_type="creature",
            target_id="2",
            damage=1,
            retaliate=True,
        )

        result = resolve(damage_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # The target creature's health went down
        self.assertEqual(new_state.creatures["2"].health, 9)

        # Initial damage event created
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, "event_damage")

        # Retaliation is returned as a child effect to be processed
        self.assertEqual(len(result.child_effects), 1)
        retaliation_effect = result.child_effects[0]
        self.assertEqual(retaliation_effect.type, "effect_damage")
        # Retaliation source is the target creature
        self.assertEqual(retaliation_effect.source_id, "2")
        self.assertEqual(retaliation_effect.source_type, "creature")
        # Retaliation targets the source creature
        self.assertEqual(retaliation_effect.target_id, "1")
        self.assertEqual(retaliation_effect.target_type, "creature")
        # Retaliation damage is the target creature's attack
        self.assertEqual(retaliation_effect.damage, 2)
        # Retaliation doesn't retaliate to avoid an infinite loop
        self.assertFalse(retaliation_effect.retaliate)

    def test_creature_to_creature_retaliation(self):
        """
        Make sure that a retaliation effect does not generate another
        retaliation event even if it otherwise would.
        """
        target_creature = Creature(
            creature_id="2",
            card_id="card_2",
            name="test",
            attack=2,
            attack_max=2,
            health=10,
            health_max=10,
            exhausted=False,
        )

        self.game_state.creatures["1"] = self.creature
        self.game_state.creatures["2"] = target_creature
        self.game_state.board['side_a'] = ["1"]
        self.game_state.board['side_b'] = ["2"]
        damage_effect = DamageEffect(
            side="side_a",
            damage_type="physical",
            source_type="creature",
            source_id="1",
            target_type="creature",
            target_id="2",
            damage=1,
            retaliate=False,
        )

        result = resolve(damage_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))

        # Only one event created (the initial damage), no retaliation
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, "event_damage")

    def test_hero_to_creature_damage(self):
        self.creature.health = 10
        self.game_state.creatures["1"] = self.creature
        self.game_state.board['side_b'] = ["1"]
        damage_effect = DamageEffect(
            side="side_a",
            damage_type="physical",
            source_type="hero",
            source_id="1",
            target_type="creature",
            target_id="1",
            damage=1,
        )

        result = resolve(damage_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        new_state = result.new_state

        # The target creature's health went down
        self.assertEqual(new_state.creatures["1"].health, 9)

        # Initial damage event created
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, "event_damage")

        # Retaliation is returned as a child effect to be processed
        self.assertEqual(len(result.child_effects), 1)
        retaliation_effect = result.child_effects[0]
        self.assertEqual(retaliation_effect.type, "effect_damage")
        # Creatures retaliate against heroes
        self.assertFalse(retaliation_effect.retaliate)
        self.assertEqual(retaliation_effect.source_id, "1")
        self.assertEqual(retaliation_effect.source_type, "creature")
        self.assertEqual(retaliation_effect.target_id, "1")
        self.assertEqual(retaliation_effect.target_type, "hero")

    def test_hero_to_hero_damage(self):
        self.game_state.heroes['side_a'].health = 10
        self.game_state.heroes['side_b'].health = 10
        damage_effect = DamageEffect(
            side="side_a",
            damage_type="physical",
            source_type="hero",
            source_id="1",
            target_type="hero",
            target_id="2",
            damage=1,
        )
        result = resolve(damage_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))
        self.assertEqual(result.new_state.heroes['side_b'].health, 9)

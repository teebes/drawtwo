"""
Tests for damage effects and combat mechanics.
"""
from apps.builder.schemas import HeroPower, DamageAction
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.schemas.engine import Success
from apps.gameplay.schemas.effects import DamageEffect, UseHeroEffect
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

    def test_hero_power_creature_retaliation(self):
        """
        Test that when a hero uses a power to damage a creature,
        the creature retaliates against the hero.
        """
        # Set up hero with the specified power
        self.game_state.heroes['side_a'].hero_power = HeroPower(
            name="Small Damage",
            actions=[
                DamageAction(
                    scope="single",
                    action="damage",
                    amount=2,
                    target="enemy",
                )
            ],
            description="Deal 2 damage to an enemy.",
        )
        self.game_state.heroes['side_a'].exhausted = False

        # Create a creature with 5 health on opponent's side
        target_creature = Creature(
            creature_id="enemy_creature",
            card_id="card_enemy",
            name="Enemy Creature",
            attack=3,
            attack_max=3,
            health=5,
            health_max=5,
            exhausted=False,
        )
        self.game_state.creatures["enemy_creature"] = target_creature
        self.game_state.board['side_b'] = ["enemy_creature"]

        # Use hero power to damage the creature
        hero_a_id = self.game_state.heroes['side_a'].hero_id
        use_hero_effect = UseHeroEffect(
            side="side_a",
            source_id=hero_a_id,
            target_type="creature",
            target_id="enemy_creature",
        )

        result = resolve(use_hero_effect, self.game_state)
        self.assertTrue(isinstance(result, Success))

        # Process child effects (the damage effect from the hero power)
        new_state = result.new_state
        child_effects = result.child_effects

        # Find the damage effect
        damage_effect = None
        for effect in child_effects:
            if effect.type == "effect_damage":
                damage_effect = effect
                break

        self.assertIsNotNone(damage_effect, "Hero power should create a damage effect")
        self.assertEqual(damage_effect.damage, 2)
        self.assertEqual(damage_effect.target_id, "enemy_creature")

        # Resolve the damage effect
        damage_result = resolve(damage_effect, new_state)
        self.assertTrue(isinstance(damage_result, Success))

        # The creature should have taken 2 damage (5 -> 3)
        self.assertEqual(damage_result.new_state.creatures["enemy_creature"].health, 3)

        # The creature should retaliate against the hero
        # This test should fail because currently retaliate=False is set in compile_action
        self.assertGreater(
            len(damage_result.child_effects),
            0,
            "Creature should retaliate against hero when damaged by hero power"
        )

        retaliation_effect = damage_result.child_effects[0]
        self.assertEqual(retaliation_effect.type, "effect_damage")
        self.assertEqual(retaliation_effect.source_type, "creature")
        self.assertEqual(retaliation_effect.source_id, "enemy_creature")
        self.assertEqual(retaliation_effect.target_type, "hero")
        self.assertEqual(retaliation_effect.target_id, hero_a_id)
        self.assertEqual(retaliation_effect.damage, 3)  # Creature's attack
        self.assertFalse(retaliation_effect.retaliate)  # Retaliation doesn't retaliate

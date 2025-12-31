"""
Tests for trait processing and effects.
"""
from apps.builder.schemas import (
    Battlecry,
    BuffAction,
    Charge,
    DamageAction,
    DeathRattle,
    DrawAction,
    RemoveAction,
    SummonAction,
    Unique,
)
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.engine.handlers import spawn_creature
from apps.gameplay.schemas.engine import Success
from apps.gameplay.schemas.effects import PlayEffect, DrawEffect, RemoveEffect, SummonEffect
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
            traits=[
                Battlecry(
                    actions=[
                        DamageAction(amount=1, target="enemy", damage_type="spell")
                    ]
                )
            ],
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
        #self.assertEqual(result.child_effects[0].retaliate, False)

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

    def test_phoenix_deathrattle_resummons_itself(self):
        phoenix_template = CardInPlay(
            card_type="creature",
            card_id="",
            template_slug="phoenix",
            name="Phoenix",
            description="On death: rise from the ashes.",
            attack=5,
            health=5,
            cost=7,
            traits=[
                DeathRattle(actions=[SummonAction(target="phoenix")]),
                Unique(),
            ],
        )
        self.game_state.summonable_cards["phoenix"] = phoenix_template

        killer_card = CardInPlay(
            card_type="creature",
            card_id="1",
            template_slug="killer-card",
            name="Killer Card",
            attack=2,
            health=2,
            cost=1,
        )
        phoenix_card = CardInPlay(
            card_type="creature",
            card_id="2",
            template_slug="phoenix",
            name="Phoenix",
            attack=5,
            health=5,
            cost=7,
            traits=[
                DeathRattle(actions=[SummonAction(target="phoenix")]),
                Unique(),
            ],
        )

        self.game_state.cards["1"] = killer_card
        self.game_state.cards["2"] = phoenix_card

        killer_creature = spawn_creature(
            card=killer_card,
            state=self.game_state,
            side="side_a",
        )
        phoenix_creature = spawn_creature(
            card=phoenix_card,
            state=self.game_state,
            side="side_b",
        )

        # Mimic the board cleanup that happens when a creature dies.
        self.game_state.board["side_b"].remove(phoenix_creature.creature_id)
        phoenix_creature.health = 0

        death_event = CreatureDeathEvent(
            side="side_b",
            creature=phoenix_creature,
            source_type="creature",
            source_id=killer_creature.creature_id,
            target_type="creature",
            target_id=phoenix_creature.creature_id,
        )

        trait_result = traits.apply(self.game_state, death_event)
        self.assertEqual(len(trait_result.child_effects), 1)
        summon_effect = trait_result.child_effects[0]
        self.assertIsInstance(summon_effect, SummonEffect)
        self.assertEqual(summon_effect.target, "phoenix")

        # Trim non-numeric helper cards so the summon handler can assign a new ID.
        non_numeric_keys = [key for key in trait_result.new_state.cards if key.startswith("card_")]
        for key in non_numeric_keys:
            trait_result.new_state.cards.pop(key)

        summon_result = resolve(summon_effect, trait_result.new_state)
        self.assertTrue(isinstance(summon_result, Success))
        final_state = summon_result.new_state

        self.assertEqual(len(final_state.board["side_b"]), 1)
        summoned_creature_id = final_state.board["side_b"][0]
        summoned_creature = final_state.creatures[summoned_creature_id]
        summoned_card = final_state.cards[summoned_creature.card_id]
        self.assertEqual(summoned_card.template_slug, "phoenix")
        self.assertEqual(summoned_creature.name, "Phoenix")
        self.assertEqual(summoned_creature.health, 5)


class TestRemoveAction(GamePlayTestBase):
    """Tests for the Remove action (removes creature without triggering deathrattle)."""

    def test_remove_action_single(self):
        """Test that remove action removes a single creature."""
        # Create a target creature on side_b
        target_card = CardInPlay(
            card_type="creature",
            card_id="target_1",
            template_slug="target-card",
            name="Target Card",
            attack=2,
            health=3,
            cost=2,
            traits=[],
        )
        target_creature = spawn_creature(
            card=target_card,
            state=self.game_state,
            side="side_b",
        )

        # Verify creature is on board
        self.assertEqual(len(self.game_state.board["side_b"]), 1)
        self.assertIn(target_creature.creature_id, self.game_state.creatures)

        # Create battlecry card with remove action
        remove_card = CardInPlay(
            card_type="creature",
            card_id="remover_1",
            template_slug="remover-card",
            name="Remover Card",
            attack=1,
            health=1,
            cost=1,
            traits=[Battlecry(actions=[RemoveAction(target="enemy")])],
        )
        self.game_state.cards["remover_1"] = remove_card

        # Create play event targeting the creature
        play_event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="remover_1",
            position=0,
            target_type="creature",
            target_id=target_creature.creature_id,
        )

        # Process battlecry
        result = traits.apply(self.game_state, play_event)
        self.assertEqual(len(result.child_effects), 1)
        self.assertIsInstance(result.child_effects[0], RemoveEffect)
        self.assertEqual(result.child_effects[0].target_id, target_creature.creature_id)

        # Resolve the remove effect
        remove_result = resolve(result.child_effects[0], self.game_state)
        self.assertIsInstance(remove_result, Success)

        # Verify creature was removed from board
        self.assertEqual(len(remove_result.new_state.board["side_b"]), 0)

    def test_remove_does_not_trigger_deathrattle(self):
        """Test that remove does NOT trigger deathrattle effects."""
        # Create a creature with deathrattle
        deathrattle_card = CardInPlay(
            card_type="creature",
            card_id="rattling_1",
            template_slug="rattling-card",
            name="Rattling Card",
            attack=1,
            health=1,
            cost=1,
            traits=[DeathRattle(actions=[DrawAction(amount=1)])],
        )
        rattling_creature = spawn_creature(
            card=deathrattle_card,
            state=self.game_state,
            side="side_b",
        )

        # Create a remove effect
        remove_effect = RemoveEffect(
            side="side_a",
            source_type="creature",
            source_id="remover_1",
            target_type="creature",
            target_id=rattling_creature.creature_id,
        )

        # Resolve the remove effect
        result = resolve(remove_effect, self.game_state)
        self.assertIsInstance(result, Success)

        # Verify creature was removed
        self.assertEqual(len(result.new_state.board["side_b"]), 0)

        # Verify RemoveEvent was emitted (not CreatureDeathEvent)
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].type, "event_remove")

        # Verify no child effects (deathrattle should NOT trigger)
        self.assertEqual(len(result.child_effects), 0)

    def test_remove_action_all_scope(self):
        """Test that remove action with 'all' scope removes all enemy creatures."""
        # Create multiple creatures on side_b
        for i in range(3):
            creature_card = CardInPlay(
                card_type="creature",
                card_id=f"creature_{i}",
                template_slug=f"creature-{i}",
                name=f"Creature {i}",
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

        # Verify 3 creatures on board
        self.assertEqual(len(self.game_state.board["side_b"]), 3)

        # Create battlecry card with remove all action
        remove_all_card = CardInPlay(
            card_type="creature",
            card_id="remover_all",
            template_slug="remover-all-card",
            name="Remove All Card",
            attack=1,
            health=1,
            cost=5,
            traits=[Battlecry(actions=[RemoveAction(target="enemy", scope="all")])],
        )
        self.game_state.cards["remover_all"] = remove_all_card

        # Create play event
        play_event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="remover_all",
            position=0,
        )

        # Process battlecry
        result = traits.apply(self.game_state, play_event)
        self.assertEqual(len(result.child_effects), 3)  # Should create 3 remove effects

        # Resolve all remove effects
        new_state = self.game_state
        for effect in result.child_effects:
            resolve_result = resolve(effect, new_state)
            new_state = resolve_result.new_state

        # Verify all creatures were removed
        self.assertEqual(len(new_state.board["side_b"]), 0)


class TestBuffAction(GamePlayTestBase):
    """Tests for the Buff action (buffs creature stats)."""

    def test_battlecry_buff_attack_single(self):
        """Test buff action targeting a single creature's attack."""
        # Create a target creature on the same side
        target_card = CardInPlay(
            card_type="creature",
            card_id="target_1",
            template_slug="target-card",
            name="Target Card",
            attack=2,
            health=3,
            cost=2,
            traits=[],
        )
        target_creature = spawn_creature(
            card=target_card,
            state=self.game_state,
            side="side_a",
        )
        self.game_state.board["side_a"] = [target_creature.creature_id]

        # Create battlecry card with buff attack action
        buff_card = CardInPlay(
            card_type="creature",
            card_id="buffer",
            template_slug="buffer-card",
            name="Buffer Card",
            attack=1,
            health=1,
            cost=3,
            traits=[Battlecry(actions=[BuffAction(attribute="attack", amount=2, target="creature", scope="single")])],
        )
        self.game_state.cards["buffer"] = buff_card

        # Create play event targeting the creature
        play_event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="buffer",
            position=0,
            target_type="creature",
            target_id=target_creature.creature_id,
        )

        # Process battlecry
        result = traits.apply(self.game_state, play_event)
        self.assertEqual(len(result.child_effects), 1)
        self.assertEqual(result.child_effects[0].type, "effect_buff")
        self.assertEqual(result.child_effects[0].attribute, "attack")
        self.assertEqual(result.child_effects[0].amount, 2)

        # Resolve the buff effect
        resolve_result = resolve(result.child_effects[0], self.game_state)
        new_state = resolve_result.new_state

        # Verify the creature's attack was buffed
        buffed_creature = new_state.creatures[target_creature.creature_id]
        self.assertEqual(buffed_creature.attack, 4)  # 2 + 2
        self.assertEqual(buffed_creature.attack_max, 4)  # max should also increase
        self.assertEqual(buffed_creature.health, 3)  # health unchanged

    def test_battlecry_buff_health_single(self):
        """Test buff action targeting a single creature's health."""
        # Create a target creature on the same side
        target_card = CardInPlay(
            card_type="creature",
            card_id="target_2",
            template_slug="target-card-2",
            name="Target Card 2",
            attack=2,
            health=3,
            cost=2,
            traits=[],
        )
        target_creature = spawn_creature(
            card=target_card,
            state=self.game_state,
            side="side_a",
        )
        self.game_state.board["side_a"] = [target_creature.creature_id]

        # Create battlecry card with buff health action
        buff_card = CardInPlay(
            card_type="creature",
            card_id="health_buffer",
            template_slug="health-buffer-card",
            name="Health Buffer Card",
            attack=1,
            health=1,
            cost=3,
            traits=[Battlecry(actions=[BuffAction(attribute="health", amount=3, target="creature", scope="single")])],
        )
        self.game_state.cards["health_buffer"] = buff_card

        # Create play event targeting the creature
        play_event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="health_buffer",
            position=0,
            target_type="creature",
            target_id=target_creature.creature_id,
        )

        # Process battlecry
        result = traits.apply(self.game_state, play_event)
        self.assertEqual(len(result.child_effects), 1)
        self.assertEqual(result.child_effects[0].type, "effect_buff")

        # Resolve the buff effect
        resolve_result = resolve(result.child_effects[0], self.game_state)
        new_state = resolve_result.new_state

        # Verify the creature's health was buffed
        buffed_creature = new_state.creatures[target_creature.creature_id]
        self.assertEqual(buffed_creature.attack, 2)  # attack unchanged
        self.assertEqual(buffed_creature.health, 6)  # 3 + 3
        self.assertEqual(buffed_creature.health_max, 6)  # max should also increase

    def test_battlecry_buff_all(self):
        """Test buff action with scope 'all' targeting all friendly creatures."""
        # Create multiple creatures on the same side
        for i in range(3):
            card = CardInPlay(
                card_type="creature",
                card_id=f"target_{i}",
                template_slug=f"target-card-{i}",
                name=f"Target Card {i}",
                attack=1,
                health=2,
                cost=2,
                traits=[],
            )
            spawn_creature(
                card=card,
                state=self.game_state,
                side="side_a",
            )

        # Verify 3 creatures on board
        self.assertEqual(len(self.game_state.board["side_a"]), 3)

        # Create battlecry card with buff all action
        buff_all_card = CardInPlay(
            card_type="creature",
            card_id="buffer_all",
            template_slug="buffer-all-card",
            name="Buffer All Card",
            attack=1,
            health=1,
            cost=5,
            traits=[Battlecry(actions=[BuffAction(attribute="attack", amount=1, target="creature", scope="all")])],
        )
        self.game_state.cards["buffer_all"] = buff_all_card

        # Create play event
        play_event = PlayEvent(
            side="side_a",
            source_type="card",
            source_id="buffer_all",
            position=0,
        )

        # Process battlecry
        result = traits.apply(self.game_state, play_event)
        self.assertEqual(len(result.child_effects), 3)  # Should create 3 buff effects

        # Resolve all buff effects
        new_state = self.game_state
        for effect in result.child_effects:
            resolve_result = resolve(effect, new_state)
            new_state = resolve_result.new_state

        # Verify all creatures were buffed
        for creature_id in new_state.board["side_a"]:
            creature = new_state.creatures[creature_id]
            self.assertEqual(creature.attack, 2)  # 1 + 1
            self.assertEqual(creature.attack_max, 2)
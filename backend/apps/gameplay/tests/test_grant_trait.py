from pydantic import TypeAdapter, ValidationError

from apps.builder.schemas import Action, Battlecry, GrantTraitAction, Taunt
from apps.gameplay.agents.legal import list_legal_commands
from apps.gameplay.agents.policies.smart import SmartPolicy
from apps.gameplay.agents.simulator import apply_command, apply_effects
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.engine.handlers import spawn_creature
from apps.gameplay.schemas.commands import PlayCardCommand
from apps.gameplay.schemas.effects import (
    AttackEffect,
    DamageEffect,
    Effect,
    GrantTraitEffect,
    RemoveEffect,
    SilenceEffect,
)
from apps.gameplay.schemas.engine import Rejected, Success
from apps.gameplay.schemas.events import Event
from apps.gameplay.schemas.game import CardInPlay, GameState
from apps.gameplay.schemas.updates import GameUpdate
from apps.gameplay.tests import GamePlayTestBase


class TestGrantTraitAction(GamePlayTestBase):
    def make_state(self, side="side_a", count=2):
        state = self.game_state.model_copy(deep=True)
        state.active = side
        state.phase = "main"
        state.mana_pool[side] = 10
        for index in range(count):
            self.add_creature(state, side, f"neighbor-{index}")
        other_side = "side_b" if side == "side_a" else "side_a"
        self.add_creature(state, other_side, "enemy")
        state.cards["guardian"] = CardInPlay(
            card_id="guardian",
            card_type="creature",
            template_slug="guardian",
            name="Guardian",
            cost=1,
            attack=1,
            health=3,
            traits=[
                Battlecry(actions=[GrantTraitAction(trait="taunt", scope="adjacent")])
            ],
        )
        state.hands[side] = ["guardian"]
        return state

    @staticmethod
    def add_creature(state, side, name):
        card = CardInPlay(
            card_id=name,
            card_type="creature",
            template_slug=name,
            name=name,
            attack=1,
            health=3,
        )
        state.cards[name] = card
        return spawn_creature(card, state, side, len(state.board[side]))

    @staticmethod
    def has_taunt(creature):
        return any(trait.type == "taunt" for trait in creature.traits)

    def play_guardian(self, state, position):
        result = apply_command(
            state,
            state.active,
            PlayCardCommand(card_id="guardian", position=position),
        )
        self.assertEqual(result.errors, [])
        return result

    def test_grants_only_immediate_neighbors_for_both_sides_and_board_edges(self):
        for side in ("side_a", "side_b"):
            for count, position in ((0, 0), (1, 0), (1, 1), (4, 0), (4, 2), (4, 4)):
                with self.subTest(side=side, count=count, position=position):
                    state = self.make_state(side, count)
                    original_board = state.board[side][:]
                    expected = set(original_board[max(0, position - 1) : position + 1])
                    result = self.play_guardian(state, position)
                    actual = {
                        creature.creature_id
                        for creature in result.state.creatures.values()
                        if self.has_taunt(creature)
                    }
                    self.assertEqual(actual, expected)
                    self.assertEqual(len(result.state.board[side]), count + 1)
                    self.assertEqual(result.state.hands[side], [])
                    self.assertEqual(result.state.mana_used[side], 1)
                    self.assertTrue(
                        all(
                            not card.has_trait("taunt")
                            for card in result.state.cards.values()
                        )
                    )

    def test_grants_round_trip_through_saved_actions_effects_events_and_updates(self):
        state = self.make_state()
        state = GameState.model_validate_json(state.model_dump_json())
        result = self.play_guardian(state, 1)
        events = TypeAdapter(list[Event]).validate_python(result.events)
        all_updates = TypeAdapter(list[GameUpdate]).validate_python(result.updates)
        grants = [e for e in events if e.type == "event_grant_trait"]
        updates = [u for u in all_updates if u.type == "update_grant_trait"]
        self.assertEqual(len(grants), 2)
        self.assertEqual(len(updates), 2)
        for event, update in zip(grants, updates):
            self.assertEqual(event.source_id, "guardian")
            self.assertEqual(event.trait, "taunt")
            self.assertEqual(update.target_id, event.target_id)
            self.assertEqual(update.trait, "taunt")
            self.assertEqual(
                TypeAdapter(Event).validate_json(event.model_dump_json()), event
            )
            self.assertEqual(
                TypeAdapter(GameUpdate).validate_json(update.model_dump_json()), update
            )
        effect = GrantTraitEffect(
            side="side_a",
            source_id="guardian",
            target_id=grants[0].target_id,
            trait="taunt",
        )
        self.assertEqual(
            TypeAdapter(Effect).validate_json(effect.model_dump_json()), effect
        )
        restored = GameState.model_validate_json(result.state.model_dump_json())
        self.assertTrue(self.has_taunt(restored.creatures[grants[0].target_id]))

    def test_existing_taunt_is_not_duplicated_or_reported_as_a_new_grant(self):
        state = self.make_state()
        left = state.board["side_a"][0]
        state.creatures[left].traits = [Taunt()]
        result = self.play_guardian(state, 1)
        self.assertEqual(
            [t.type for t in result.state.creatures[left].traits], ["taunt"]
        )
        grants = [e for e in result.events if e["type"] == "event_grant_trait"]
        self.assertEqual(len(grants), 1)
        self.assertNotEqual(grants[0]["target_id"], left)

    def test_grant_survives_source_death_and_does_not_affect_later_neighbors(self):
        played = self.play_guardian(self.make_state(), 1)
        state = played.state
        source = state.board["side_a"][1]
        later = self.add_creature(state, "side_a", "later")
        # Place a new creature beside the source; this must not behave as an aura.
        state.board["side_a"].remove(later.creature_id)
        state.board["side_a"].insert(1, later.creature_id)
        result = apply_effects(
            state,
            [
                DamageEffect(
                    side="side_b",
                    source_type="hero",
                    source_id=state.heroes["side_b"].hero_id,
                    target_type="creature",
                    target_id=source,
                    damage=99,
                    retaliate=False,
                )
            ],
        )
        self.assertEqual(result.errors, [])
        self.assertNotIn(source, result.state.board["side_a"])
        self.assertFalse(self.has_taunt(result.state.creatures[later.creature_id]))
        self.assertEqual(
            sum(
                self.has_taunt(result.state.creatures[cid])
                for cid in result.state.board["side_a"]
            ),
            2,
        )

    def test_granted_taunt_blocks_attacks_and_silence_removes_it(self):
        state = self.play_guardian(self.make_state(), 1).state
        state.active = "side_b"
        attacker = state.board["side_b"][0]
        state.creatures[attacker].exhausted = False
        attack = AttackEffect(
            side="side_b",
            card_id=attacker,
            target_type="hero",
            target_id=state.heroes["side_a"].hero_id,
        )
        blocked = resolve(attack, state)
        self.assertIsInstance(blocked, Rejected)
        self.assertIn("Taunt", blocked.reason)
        for target_id in state.board["side_a"]:
            if not self.has_taunt(state.creatures[target_id]):
                continue
            silenced = resolve(
                SilenceEffect(
                    side="side_b",
                    source_type="hero",
                    source_id=state.heroes["side_b"].hero_id,
                    target_id=target_id,
                ),
                state,
            )
            self.assertIsInstance(silenced, Success)
            self.assertEqual(silenced.events[0].removed_traits, ["taunt"])
            state = silenced.new_state
        self.assertIsInstance(resolve(attack, state), Success)

    def test_removed_neighbor_is_skipped_when_queued_grant_resolves(self):
        state = self.make_state()
        target = state.board["side_a"][0]
        grant = GrantTraitEffect(
            side="side_a", source_id="guardian", target_id=target, trait="taunt"
        )
        result = apply_effects(
            state,
            [
                RemoveEffect(
                    side="side_b", source_type="hero", source_id="2", target_id=target
                ),
                grant,
            ],
        )
        self.assertEqual(result.errors, [])
        self.assertFalse(self.has_taunt(result.state.creatures[target]))
        self.assertFalse(any(e["type"] == "event_grant_trait" for e in result.events))

    def test_single_scope_grants_only_to_the_played_creature(self):
        state = self.make_state()
        state.cards["guardian"].traits[0].actions = [GrantTraitAction(trait="taunt")]
        result = self.play_guardian(state, 1)
        self.assertEqual(
            [
                cid
                for cid in result.state.board["side_a"]
                if self.has_taunt(result.state.creatures[cid])
            ],
            [result.state.board["side_a"][1]],
        )

    def test_spell_has_no_source_creature_and_does_not_grant_to_a_selected_target(self):
        state = self.make_state()
        state.cards["guardian"].card_type = "spell"
        result = apply_command(
            state,
            "side_a",
            PlayCardCommand(
                card_id="guardian",
                position=0,
                target_type="creature",
                target_id=state.board["side_a"][0],
            ),
        )
        self.assertEqual(result.errors, [])
        self.assertFalse(
            any(self.has_taunt(c) for c in result.state.creatures.values())
        )

    def test_ai_can_play_without_a_target_at_every_position_including_empty_board(self):
        for count in (0, 2):
            state = self.make_state(count=count)
            commands = [
                c
                for c in list_legal_commands(state, "side_a")
                if isinstance(c, PlayCardCommand)
            ]
            self.assertEqual([c.position for c in commands], list(range(count + 1)))
            self.assertTrue(all(c.target_id is None for c in commands))

    def test_smart_ai_prefers_granting_to_two_neighbors(self):
        state = self.make_state()
        policy = SmartPolicy()
        command = policy.select_command(
            state, list_legal_commands(state, "side_a"), budget_ms=1000
        )
        self.assertIsInstance(command, PlayCardCommand)
        self.assertEqual(command.position, 1)

    def test_manifest_rejects_unsupported_traits_targets_and_scopes(self):
        for field, value in (
            ("trait", "unknown"),
            ("target", "hero"),
            ("scope", "cleave"),
        ):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                TypeAdapter(Action).validate_python(
                    {
                        "action": "grant_trait",
                        "trait": "taunt",
                        field: value,
                    }
                )

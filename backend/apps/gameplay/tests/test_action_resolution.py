from pydantic import TypeAdapter

from apps.builder.schemas import (
    Battlecry,
    ClearAction,
    DamageAction,
    DeathRattle,
    DrawAction,
    Stealth,
    SummonAction,
    Taunt,
    Triggered,
)
from apps.gameplay.agents.simulator import apply_effects
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.engine.handlers import spawn_creature
from apps.gameplay.models import Game
from apps.gameplay.schemas.effects import ClearEffect, DamageEffect, Effect, PlayEffect
from apps.gameplay.schemas.events import Event
from apps.gameplay.schemas.game import CardInPlay
from apps.gameplay.schemas.updates import GameUpdate
from apps.gameplay.services import GameService
from apps.gameplay.tests import GamePlayTestBase, ServiceTestsBase


def damage_action(target, amount=1):
    return DamageAction(amount=amount, target=target, scope="all", damage_type="spell")


def prepare_blast(state, side, order=("enemy", "friendly")):
    state.active = side
    state.phase = "main"
    state.mana_pool[side] = 4
    card_id = str(max((int(cid) for cid in state.cards), default=0) + 1)
    state.cards[card_id] = CardInPlay(
        card_type="creature",
        card_id=card_id,
        template_slug="blaster",
        name="Blaster",
        cost=4,
        attack=4,
        health=4,
        traits=[Battlecry(actions=[damage_action(target) for target in order])],
    )
    state.hands[side].append(card_id)
    return PlayEffect(side=side, source_id=card_id, position=len(state.board[side]))


def add_creature(state, side, name, health=2, traits=()):
    card_id = str(max((int(cid) for cid in state.cards), default=0) + 1)
    card = CardInPlay(
        card_type="creature",
        card_id=card_id,
        template_slug=name,
        name=name,
        attack=10,
        health=health,
        traits=list(traits),
    )
    state.cards[card_id] = card
    return spawn_creature(card, state, side, position=len(state.board[side]))


class TestActionResolution(GamePlayTestBase):
    def test_damage_events_preserve_damage_type_for_heroes_and_creatures(self):
        for side in ("side_a", "side_b"):
            for damage_type in ("physical", "spell"):
                for target_type in ("hero", "creature"):
                    with self.subTest(
                        side=side, damage_type=damage_type, target_type=target_type
                    ):
                        state = self.game_state.model_copy(deep=True)
                        creature = add_creature(state, side, "target")
                        target_id = (
                            state.heroes[side].hero_id
                            if target_type == "hero"
                            else creature.creature_id
                        )
                        result = resolve(
                            DamageEffect(
                                side=side,
                                source_type="hero",
                                source_id=state.heroes[side].hero_id,
                                target_type=target_type,
                                target_id=target_id,
                                damage=1,
                                damage_type=damage_type,
                                retaliate=False,
                            ),
                            state,
                        )
                        event = TypeAdapter(Event).validate_json(
                            result.events[0].model_dump_json()
                        )
                        self.assertEqual(event.damage_type, damage_type)
                        self.assertEqual(event.damage_taken, 1)

    def test_clear_from_deathrattle_and_trigger_keeps_source_through_updates(self):
        for side in ("side_a", "side_b"):
            opposing_side = "side_b" if side == "side_a" else "side_a"
            for target in ("both", "own", "opponent"):
                for trait_type in ("deathrattle", "triggered"):
                    with self.subTest(side=side, target=target, trait=trait_type):
                        state = self.game_state.model_copy(deep=True)
                        action = ClearAction(target=target)
                        trait = (
                            DeathRattle(actions=[action])
                            if trait_type == "deathrattle"
                            else Triggered(
                                when={"event": "damage", "target": {"self": True}},
                                actions=[action],
                            )
                        )
                        source = add_creature(
                            state,
                            side,
                            "clear-source",
                            health=1 if trait_type == "deathrattle" else 2,
                            traits=[trait],
                        )
                        for board_side in (side, opposing_side):
                            add_creature(
                                state,
                                board_side,
                                "bystander",
                                traits=[DeathRattle(actions=[DrawAction(amount=1)])],
                            )
                        expected_board = {
                            board_side: ids.copy()
                            for board_side, ids in state.board.items()
                        }
                        if trait_type == "deathrattle":
                            expected_board[side].remove(source.creature_id)
                        for board_side in (side, opposing_side):
                            if target == "both" or board_side == (
                                side if target == "own" else opposing_side
                            ):
                                expected_board[board_side] = []

                        effect = ClearEffect(
                            side=side,
                            source_type="creature",
                            source_id=source.creature_id,
                            target=target,
                        )
                        self.assertEqual(
                            TypeAdapter(Effect).validate_json(effect.model_dump_json()),
                            effect,
                        )
                        result = apply_effects(
                            state,
                            [
                                DamageEffect(
                                    side=opposing_side,
                                    source_type="hero",
                                    source_id=state.heroes[opposing_side].hero_id,
                                    target_type="creature",
                                    target_id=source.creature_id,
                                    damage_type="spell",
                                    damage=1,
                                )
                            ],
                        )
                        self.assertEqual(result.errors, [])
                        self.assertEqual(result.state.board, expected_board)
                        self.assertEqual(result.winner, "none")
                        events = TypeAdapter(list[Event]).validate_python(result.events)
                        updates = TypeAdapter(list[GameUpdate]).validate_python(
                            result.updates
                        )
                        clears = [e for e in events if e.type == "event_clear"]
                        clear_updates = [u for u in updates if u.type == "update_clear"]
                        self.assertEqual(len(clears), 1)
                        self.assertEqual(len(clear_updates), 1)
                        for item in [*clears, *clear_updates]:
                            self.assertEqual(item.source_type, "creature")
                            self.assertEqual(item.source_id, source.creature_id)
                            self.assertEqual(item.side, side)
                            self.assertEqual(item.target, target)
                        # Clearing bystanders must not fire their Draw deathrattles.
                        self.assertEqual(
                            len(
                                [e for e in events if e.type == "event_creature_death"]
                            ),
                            int(trait_type == "deathrattle"),
                        )

    def test_blast_hits_both_sides_in_action_order_including_itself_and_stealth(self):
        for side in ("side_a", "side_b"):
            opposing_side = "side_b" if side == "side_a" else "side_a"
            for order in (("enemy", "friendly"), ("friendly", "enemy")):
                with self.subTest(side=side, order=order):
                    state = self.game_state.model_copy(deep=True)
                    ally = add_creature(state, side, "ally")
                    enemy = add_creature(
                        state,
                        opposing_side,
                        "enemy",
                        health=1,
                        traits=[Stealth(), Taunt()],
                    )
                    result = apply_effects(state, [prepare_blast(state, side, order)])
                    self.assertEqual(result.errors, [])
                    self.assertEqual(result.state.mana_used[side], 4)
                    self.assertEqual(result.state.creatures[ally.creature_id].health, 1)
                    self.assertNotIn(
                        enemy.creature_id, result.state.board[opposing_side]
                    )
                    blaster = result.state.creatures[result.state.board[side][-1]]
                    self.assertEqual((blaster.attack, blaster.health), (4, 3))
                    self.assertTrue(
                        all(h.health == 9 for h in result.state.heroes.values())
                    )
                    hits = [e for e in result.events if e["type"] == "event_damage"]
                    expected_sides = (
                        [opposing_side] * 2 + [side] * 3
                        if order[0] == "enemy"
                        else [side] * 3 + [opposing_side] * 2
                    )
                    self.assertEqual([e["target_side"] for e in hits], expected_sides)
                    self.assertTrue(all(e["damage_type"] == "spell" for e in hits))
                    self.assertTrue(all(not e["is_retaliation"] for e in hits))

    def test_remaining_damage_survives_source_death_and_skips_dead_targets(self):
        for side in ("side_a", "side_b"):
            with self.subTest(side=side):
                opposing_side = "side_b" if side == "side_a" else "side_a"
                state = self.game_state.model_copy(deep=True)
                add_creature(
                    state,
                    opposing_side,
                    "mine",
                    health=1,
                    traits=[DeathRattle(actions=[damage_action("enemy", 4)])],
                )
                ally = add_creature(state, side, "ally")
                result = apply_effects(state, [prepare_blast(state, side)])
                self.assertEqual(result.errors, [])
                self.assertEqual(result.state.board[side], [])
                self.assertEqual(result.state.creatures[ally.creature_id].health, -2)
                self.assertEqual(result.state.heroes[side].health, 5)
                self.assertEqual(result.state.heroes[opposing_side].health, 9)
                self.assertEqual(result.winner, "none")

    def test_creature_deathrattle_can_end_game_before_enemy_hero_is_hit(self):
        for side in ("side_a", "side_b"):
            with self.subTest(side=side):
                opposing_side = "side_b" if side == "side_a" else "side_a"
                state = self.game_state.model_copy(deep=True)
                for hero in state.heroes.values():
                    hero.health = 1
                add_creature(
                    state,
                    opposing_side,
                    "mine",
                    health=1,
                    traits=[DeathRattle(actions=[damage_action("enemy")])],
                )
                result = apply_effects(state, [prepare_blast(state, side)])
                self.assertEqual(result.errors, [])
                self.assertEqual(result.winner, opposing_side)
                self.assertEqual(result.state.heroes[opposing_side].health, 1)

    def test_second_action_does_not_hit_creatures_summoned_during_first(self):
        state = self.game_state
        state.summonable_cards["token"] = CardInPlay(
            card_type="creature",
            card_id="token",
            template_slug="token",
            name="Token",
            attack=1,
            health=1,
        )
        add_creature(
            state,
            "side_a",
            "summoner",
            traits=[
                Triggered(
                    when={
                        "event": "damage",
                        "target": {"kind": "creature", "controller": "opponent"},
                    },
                    actions=[SummonAction(target="token")],
                )
            ],
        )
        add_creature(state, "side_b", "enemy", health=1)
        result = apply_effects(state, [prepare_blast(state, "side_a")])
        self.assertEqual(result.errors, [])
        tokens = [c for c in result.state.creatures.values() if c.name == "Token"]
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].health, 1)
        self.assertIn(tokens[0].creature_id, result.state.board["side_a"])


class TestOrderedDamageGameEnd(ServiceTestsBase):
    def test_action_order_determines_winner_and_clears_remaining_queue(self):
        for side in ("side_a", "side_b"):
            for order in (("enemy", "friendly"), ("friendly", "enemy")):
                with self.subTest(side=side, order=order):
                    game = GameService.create_game(
                        self.deck_a,
                        self.deck_b,
                        randomize_starting_player=False,
                        reuse_active_game=False,
                    )
                    state = game.game_state
                    for hero in state.heroes.values():
                        hero.health = 1
                    effect = prepare_blast(state, side, order)
                    simulated = apply_effects(state, [effect])
                    opposing_side = "side_b" if side == "side_a" else "side_a"
                    winner = side if order[0] == "enemy" else opposing_side
                    self.assertEqual(simulated.errors, [])
                    self.assertEqual(simulated.winner, winner)
                    game.state = state.model_dump(mode="json")
                    game.queue = [effect.model_dump(mode="json")]
                    game.save(update_fields=["state", "queue"])
                    GameService.step(game.id)
                    game.refresh_from_db()
                    self.assertEqual(game.status, Game.GAME_STATUS_ENDED)
                    self.assertEqual(game.winner, getattr(game, winner))
                    self.assertEqual(game.state["winner"], simulated.winner)
                    self.assertEqual(game.state["heroes"][winner]["health"], 1)
                    self.assertEqual(game.queue, [])
                    self.assertEqual(game.state["queue"], [])
                    self.assertFalse(game.actions.exists())
                    self.assertEqual(game.state["board"], simulated.state.board)

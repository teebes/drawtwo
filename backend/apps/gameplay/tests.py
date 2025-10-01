from django.test import TestCase

from apps.builder.schemas import (
    Battlecry,
    CardActionDamage,
    CardActionDraw,
    Charge,
)
from apps.gameplay.engine import resolve_event
from apps.gameplay.schemas.events import (
    ChooseAIMoveEvent,
    DealDamageEvent,
    DrawCardEvent,
    PlayCardEvent,

)
from apps.gameplay.schemas.updates import DamageUpdate, GameOverUpdate
from .schemas import GameState, CardInPlay, HeroInPlay
from .services import GameService


class GamePlayTestBase(TestCase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.game_state = GameState(
            turn=1,
            active="side_a",
            phase="start",
            event_queue=[],
            cards={},
            decks={'side_a': [], 'side_b': []},
            mana_pool={'side_a': 0, 'side_b': 0},
            mana_used={'side_a': 0, 'side_b': 0},
            board={'side_a': [], 'side_b': []},
            hands={'side_a': [], 'side_b': []},
            heroes={
                'side_a': HeroInPlay(
                    hero_id="1",
                    template_slug="hero_a",
                    health=10,
                    name="Hero A",
                    hero_power={
                        "actions": [
                            CardActionDamage(
                                amount=1,
                                target="enemy",
                            )
                        ]
                    },
                ),
                'side_b': HeroInPlay(
                    hero_id="2",
                    template_slug="hero_b",
                    health=10,
                    name="Hero B",
                    hero_power={
                        "actions": [
                            CardActionDamage(
                                amount=1,
                                target="enemy",
                            )
                        ]
                    },
                ),
            },
        )


class TestDamage(GamePlayTestBase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.minion = CardInPlay(
            card_type="minion",
            card_id="1",
            template_slug="test",
            name="test",
            attack=1,
            health=1,
            cost=1,
            exhausted=False,
        )

    def test_minion_to_hero_damage(self):
        self.game_state.cards["1"] = self.minion
        self.game_state.board['side_a'] = ["1"]
        self.game_state.event_queue.append(DealDamageEvent(
            side="side_a",
            damage_type="physical",
            source_type="card",
            source_id="1",
            target_type="hero",
            target_id="2",
            damage=1,
        ))

        resolved_event = resolve_event(self.game_state)
        new_state = resolved_event.state

        # The target hero's health went down
        self.assertEqual(new_state.heroes['side_b'].health, 9)

        # No further events created
        self.assertEqual(len(resolved_event.events), 0)

        # A DamageUpdate is created
        self.assertEqual(len(resolved_event.updates), 1)
        self.assertIsInstance(resolved_event.updates[0], DamageUpdate)

        # Attacking minion is exhausted
        self.assertTrue(new_state.cards["1"].exhausted)

    def test_minion_to_minion_damage(self):
        target_minion = CardInPlay(
            card_type="minion",
            card_id="2",
            template_slug="test",
            name="test",
            attack=2,
            health=10,
            cost=1,
            exhausted=False,
        )

        self.game_state.cards["1"] = self.minion
        self.game_state.cards["2"] = target_minion
        self.game_state.board['side_a'] = ["1"]
        self.game_state.board['side_b'] = ["2"]
        self.game_state.event_queue.append(DealDamageEvent(
            side="side_a",
            damage_type="physical",
            source_type="card",
            source_id="1",
            target_type="card",
            target_id="2",
            damage=1,
            retaliate=True,
        ))

        resolved_event = resolve_event(self.game_state)
        new_state = resolved_event.state

        # The target minion's health went down
        self.assertEqual(new_state.cards["2"].health, 9)

        # Retaliation event was created
        self.assertEqual(len(resolved_event.events), 1)
        self.assertEqual(resolved_event.events[0].type, "event_damage")
        # Retaliation targets the source minion
        self.assertEqual(resolved_event.events[0].source_id, "2")
        self.assertEqual(resolved_event.events[0].source_type, "card")
        # Retaliation source is the target minion
        self.assertEqual(resolved_event.events[0].target_id, "1")
        self.assertEqual(resolved_event.events[0].target_type, "card")
        # Retaliation damage is the target minion's attack
        self.assertEqual(resolved_event.events[0].damage, 2)
        # Retaliation doesn't retaliate to avoid an infinite loop
        self.assertFalse(resolved_event.events[0].retaliate)

    def test_minion_to_minion_retaliation(self):
        """
        Make sure that a retaliation event does not generate another
        retaliation event even if it otherwise would.
        """
        target_minion = CardInPlay(
            card_type="minion",
            card_id="2",
            template_slug="test",
            name="test",
            attack=2,
            health=10,
            cost=1,
            exhausted=False,
        )

        self.game_state.cards["1"] = self.minion
        self.game_state.cards["2"] = target_minion
        self.game_state.board['side_a'] = ["1"]
        self.game_state.board['side_b'] = ["2"]
        self.game_state.event_queue.append(DealDamageEvent(
            side="side_a",
            damage_type="physical",
            source_type="card",
            source_id="1",
            target_type="card",
            target_id="2",
            damage=1,
            retaliate=False,
        ))

        resolved_event = resolve_event(self.game_state)

        # No retaliation event was created
        self.assertEqual(len(resolved_event.events), 0)

    def test_hero_to_minion_damage(self):
        self.minion.health = 10
        self.game_state.cards["1"] = self.minion
        self.game_state.board['side_b'] = ["1"]
        self.game_state.event_queue.append(DealDamageEvent(
            side="side_a",
            damage_type="physical",
            source_type="hero",
            source_id="1",
            target_type="card",
            target_id="1",
            damage=1,
        ))

        resolved_event = resolve_event(self.game_state)
        new_state = resolved_event.state

        # The target minion's health went down
        self.assertEqual(new_state.cards["1"].health, 9)

        # Minions retaliate against heroes
        self.assertEqual(len(resolved_event.events), 1)
        self.assertEqual(resolved_event.events[0].type, "event_damage")
        self.assertEqual(resolved_event.events[0].retaliate, False)
        self.assertEqual(resolved_event.events[0].source_id, "1")
        self.assertEqual(resolved_event.events[0].source_type, "card")
        self.assertEqual(resolved_event.events[0].target_id, "1")
        self.assertEqual(resolved_event.events[0].target_type, "hero")


class TestPlayMinion(GamePlayTestBase):
    def test_play_minion_to_board(self):
        minion = CardInPlay(
            card_type="minion",
            card_id="1",
            template_slug="test",
            name="test",
            attack=1,
            health=1,
            cost=1,
            exhausted=False,
        )
        self.game_state.cards["1"] = minion
        self.game_state.hands["side_a"] = ["1"]
        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0
        self.game_state.event_queue.append(PlayCardEvent(
            side="side_a",
            card_id="1",
            position=0,
        ))
        resolved_event = resolve_event(self.game_state)
        new_state = resolved_event.state
        self.assertEqual(new_state.board["side_a"], ["1"])


class TestPlaySpell(GamePlayTestBase):

    def test_play_spell_energy_check(self):
        "EnergyError is returned if the player can't afford the spell"
        spell_card = CardInPlay(
            card_type="spell",
            card_id="1",
            template_slug="small-nuke",
            name="Small Nuke",
            cost=1,
            traits=[
                Battlecry(
                    actions=[
                        CardActionDamage(
                            amount=1,
                            target="enemy",
                        )
                    ]
                )
            ],
        )

        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 1
        self.game_state.cards["1"] = spell_card
        self.game_state.hands["side_a"] = ["1"]
        self.game_state.event_queue.append(PlayCardEvent(
            side="side_a",
            card_id="1",
            position=0,
            target_type="hero",
            target_id="2",
        ))
        resolved_event = resolve_event(self.game_state)
        self.assertEqual(resolved_event.events, [])
        self.assertEqual(resolved_event.updates, [])
        self.assertEqual(len(resolved_event.errors), 1)
        self.assertEqual(resolved_event.errors[0].type, "error_energy")

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
                        CardActionDamage(
                            amount=1,
                            target="enemy",
                        )
                    ]
                )
            ],
        )

        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0
        self.game_state.cards["1"] = spell_card
        self.game_state.hands["side_a"] = ["1"]
        self.game_state.event_queue.append(PlayCardEvent(
            side="side_a",
            card_id="1",
            position=0,
            target_type="hero",
            target_id="2",
        ))
        resolved_event = resolve_event(self.game_state)
        new_state = resolved_event.state
        self.assertEqual(resolved_event.events[0].type, 'event_damage')
        self.assertEqual(resolved_event.errors, [])
        self.assertEqual(new_state.hands["side_a"], [])
        self.assertEqual(new_state.graveyard["side_a"], ["1"])
        self.assertEqual(new_state.mana_used["side_a"], 1)


class TestTraits(GamePlayTestBase):

    def test_battlecry_draw(self):
        battlecry_draw = CardInPlay(
            card_type="minion",
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
                        CardActionDraw()
                    ],
                )
            ],
        )

        self.game_state.cards["1"] = battlecry_draw
        self.game_state.hands["side_a"] = ["1"]
        self.game_state.mana_pool["side_a"] = 1
        self.game_state.mana_used["side_a"] = 0

        play_card_event = PlayCardEvent(
            side="side_a",
            card_id="1",
            position=0,
        )

        self.game_state.event_queue.append(play_card_event)

        resolved_event = resolve_event(self.game_state)

        new_state = resolved_event.state
        self.assertEqual(new_state.decks["side_a"], [])
        self.assertEqual(new_state.board["side_a"], ["1"])
        self.assertEqual(new_state.event_queue[0].type, 'event_draw_card')


class TestEndGame(GamePlayTestBase):

    def test_decking_out_via_card_action(self):
        draw_card_event = DrawCardEvent(
            side="side_a",
            amount=1,
        )
        self.game_state.event_queue.append(draw_card_event)
        resolved_event = resolve_event(self.game_state)
        self.assertTrue(isinstance(resolved_event.updates[0], GameOverUpdate))


class TestAI(GamePlayTestBase):
    "Regression test for an AI using a charge card after it's played"

    def test_ai_uses_charge_card(self):
        charge_card = CardInPlay(
            card_type="minion",
            card_id="1",
            template_slug="charge-card",
            name="Charge Card",
            cost=1,
            attack=1,
            health=1,
            traits=[Charge()],
            exhausted=False,
        )
        self.game_state.cards["1"] = charge_card
        self.game_state.board['side_b'] = ["1"]
        self.game_state.active = "side_b"
        self.game_state.ai_sides = ["side_b"]
        self.game_state.mana_pool["side_b"] = 1
        self.game_state.mana_used["side_b"] = 1

        self.game_state.event_queue.append(ChooseAIMoveEvent(side="side_b"))

        resolved_event = resolve_event(self.game_state)
        self.assertEqual(resolved_event.events[0].type, "event_use_card")
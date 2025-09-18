from django.test import TestCase

from apps.builder.schemas import Battlecry, CardActionDraw
from apps.gameplay.engine import resolve_event
from apps.gameplay.schemas.events import PlayCardEvent, DrawCardEvent
from apps.gameplay.schemas.updates import GameOverUpdate
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
            decks={'side_a': []},
            mana_pool={'side_a': 0},
            mana_used={'side_a': 0},
            board={'side_a': []},
            hands={'side_a': []},
            heroes={'side_a': HeroInPlay(
                hero_id="1",
                template_slug="test",
                health=1,
                name="test",
            )},
        )


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
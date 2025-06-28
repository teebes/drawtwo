from django.test import TestCase

from .schemas import GameState, CardInPlay, HeroInPlay
from .services import GameService


class GameStateChangesTests(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
                hero_id=1,
                template_slug="test",
                health=1,
                name="test",
            )},
        )

    def test_draw_card(self):
        self.game_state.mana_pool['side_a'] = 1
        self.game_state.cards[1] = CardInPlay(
            card_id=1,
            template_slug="test",
            attack=1,
            health=1,
            cost=1,
        )
        self.game_state.cards[2] = CardInPlay(
            card_id=2,
            template_slug="test",
            attack=1,
            health=1,
            cost=1,
        )
        self.game_state.decks['side_a'] = [1, 2]

        game_update = GameService.draw_card(self.game_state, 'side_a')
        self.assertEqual(game_update[0].type, "draw_card")
        self.assertEqual(game_update[0].side, "side_a")
        self.assertEqual(game_update[0].data['card']['card_id'], 1)
        self.assertEqual(self.game_state.decks['side_a'], [2])
        self.assertEqual(self.game_state.hands['side_a'], [1])

        game_update = GameService.draw_card(self.game_state, 'side_a')
        self.assertEqual(game_update[0].type, "draw_card")
        self.assertEqual(game_update[0].side, "side_a")
        self.assertEqual(game_update[0].data['card']['card_id'], 2)
        self.assertEqual(self.game_state.decks['side_a'], [])
        self.assertEqual(self.game_state.hands['side_a'], [1, 2])

        with self.assertRaises(ValueError):
            GameService.draw_card(self.game_state, 'side_b')
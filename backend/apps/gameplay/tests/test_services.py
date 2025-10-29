"""
Tests for GameService - game initialization and high-level operations.
"""
from apps.gameplay.tests import ServiceTestsBase
from apps.gameplay.services import GameService


class ServiceTests(ServiceTestsBase):
    """Tests for GameService initialization."""

    def test_start_game(self):
        self.assertEqual(self.game.status, 'in_progress')
        self.assertEqual(self.game.state['turn'], 1)
        self.assertEqual(self.game.state['active'], 'side_a')
        self.assertEqual(self.game.state['phase'], 'main')
        self.assertEqual(len(self.game.state['hands']['side_a']), 4)
        self.assertEqual(len(self.game.state['hands']['side_b']), 3)


class SmokeTests(ServiceTestsBase):
    """Integration tests that process full command flows through the queue."""

    def setUp(self):
        super().setUp()
        while self.game.queue:
            GameService.step(self.game.id)
            self.game.refresh_from_db()

    def test_draw_two(self):
        from apps.gameplay.schemas.game import CardInPlay
        from apps.builder.schemas import Battlecry, DrawAction

        draw_two_card = CardInPlay(
            card_type="spell",
            card_id="10",
            template_slug="draw-two",
            name="Draw Two",
            description="Draw two cards.",
            cost=1,
            traits=[Battlecry(actions=[DrawAction(amount=2)])],
        )
        self.game.state['mana_pool']['side_a'] = 1
        self.game.state['mana_used']['side_a'] = 0
        self.game.state['cards']['10'] = draw_two_card.model_dump()
        self.game.state['hands']['side_a'].append('10')
        # Add two more cards to the deck so that we don't deck out
        for i in range(2):
            card_id = str(11+i)
            card = CardInPlay(
                card_type="creature",
                card_id=card_id,
                template_slug="test-card",
                name="Test Card",
                attack=1,
                health=1,
                cost=1,
            )
            self.game.state['cards'][card_id] = card.model_dump()
            self.game.state['decks']['side_a'].append(card_id)
        self.assertEqual(len(self.game.state['decks']['side_a']), 2)
        self.game.save()

        initial_hand_size = len(self.game.state['hands']['side_a'])

        command = {'type': 'cmd_play_card', 'card_id': '10', 'position': 0}
        GameService.process_command(self.game.id, command, 'side_a')
        self.game.refresh_from_db()
        self.assertEqual(len(self.game.state['hands']['side_a']), initial_hand_size + 1)
        self.assertEqual(len(self.game.queue), 0)
        self.assertEqual(self.game.state['board']['side_a'], [])

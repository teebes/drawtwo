"""
Tests for GameService - game initialization and high-level operations.
"""
from apps.gameplay.tests import ServiceTestsBase
from apps.gameplay.services import GameService


class ServiceTests(ServiceTestsBase):
    """Tests for GameService initialization."""

    def test_start_game(self):
        self.assertEqual(self.game.status, 'init')
        self.assertEqual(self.game.state['turn'], 0)
        self.assertEqual(self.game.state['active'], 'side_a')
        self.assertEqual(self.game.state['phase'], 'start')
        self.assertEqual(len(self.game.state['hands']['side_a']), 0)
        self.assertEqual(len(self.game.state['hands']['side_b']), 0)

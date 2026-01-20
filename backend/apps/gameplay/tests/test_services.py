"""
Tests for GameService - game initialization and high-level operations.
"""
from django.test import TestCase
from apps.authentication.models import User
from apps.builder.models import Title, HeroTemplate, CardTemplate
from apps.collection.models import Deck, DeckCard
from apps.gameplay.models import Game, MatchmakingQueue
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


class MatchmakingTests(TestCase):
    """Tests for matchmaking functionality."""

    def setUp(self):
        """Create test users, title, decks for matchmaking tests."""
        # Create two users
        self.user_a = User.objects.create_user(
            email="user_a@example.com",
            username="user_a"
        )
        self.user_b = User.objects.create_user(
            email="user_b@example.com",
            username="user_b"
        )

        # Create title and heroes
        self.title = Title.objects.create(slug='test-title', author=self.user_a)
        self.hero_a = HeroTemplate.objects.create(
            title=self.title,
            slug='hero-a',
            name="Hero A",
            health=30
        )
        self.hero_b = HeroTemplate.objects.create(
            title=self.title,
            slug='hero-b',
            name="Hero B",
            health=30
        )

        # Create decks for both users
        self.deck_a = Deck.objects.create(
            title=self.title,
            user=self.user_a,
            name="Deck A",
            hero=self.hero_a
        )
        self.deck_b = Deck.objects.create(
            title=self.title,
            user=self.user_b,
            name="Deck B",
            hero=self.hero_b
        )

        # Add some cards to both decks
        for i in range(4):
            card = CardTemplate.objects.create(
                title=self.title,
                slug=f'card-{i}',
                name=f'Card {i}',
                cost=1,
            )
            DeckCard.objects.create(deck=self.deck_a, card=card)
            DeckCard.objects.create(deck=self.deck_b, card=card)

        # Create alternate decks for testing multiple games
        self.deck_a2 = Deck.objects.create(
            title=self.title,
            user=self.user_a,
            name="Deck A2",
            hero=self.hero_a
        )
        self.deck_b2 = Deck.objects.create(
            title=self.title,
            user=self.user_b,
            name="Deck B2",
            hero=self.hero_b
        )
        # Add cards to alternate decks
        for i in range(4):
            card = CardTemplate.objects.get(slug=f'card-{i}')
            DeckCard.objects.create(deck=self.deck_a2, card=card)
            DeckCard.objects.create(deck=self.deck_b2, card=card)

    def test_prevent_duplicate_daily_ranked_games(self):
        """Test that two players cannot have multiple active daily ranked games."""
        # Create an existing active daily ranked game between user_a and user_b
        existing_game = GameService.create_game(
            self.deck_a,
            self.deck_b,
            randomize_starting_player=False,
        )
        existing_game.type = Game.GAME_TYPE_RANKED
        existing_game.ladder_type = Game.LADDER_TYPE_DAILY
        existing_game.status = Game.GAME_STATUS_IN_PROGRESS
        existing_game.save()

        # Queue both users for daily ranked matchmaking with DIFFERENT decks
        # Daily games should prevent matching even with different decks
        queue_a = MatchmakingQueue.objects.create(
            user=self.user_a,
            deck=self.deck_a2,  # Use alternate deck
            elo_rating=1500,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_DAILY,
        )
        queue_b = MatchmakingQueue.objects.create(
            user=self.user_b,
            deck=self.deck_b2,  # Use alternate deck
            elo_rating=1500,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_DAILY,
        )

        # Process matchmaking for daily ladder
        matches_created = GameService.process_matchmaking(
            self.title.id,
            ladder_type=Game.LADDER_TYPE_DAILY
        )

        # Verify that no new matches were created
        self.assertEqual(matches_created, 0)

        # Verify that both queue entries are still in QUEUED status
        queue_a.refresh_from_db()
        queue_b.refresh_from_db()
        self.assertEqual(queue_a.status, MatchmakingQueue.STATUS_QUEUED)
        self.assertEqual(queue_b.status, MatchmakingQueue.STATUS_QUEUED)

        # Verify only 1 game exists (the original)
        game_count = Game.objects.filter(
            type=Game.GAME_TYPE_RANKED,
            ladder_type=Game.LADDER_TYPE_DAILY,
        ).count()
        self.assertEqual(game_count, 1)

    def test_allow_duplicate_rapid_ranked_games(self):
        """Test that two players CAN have multiple active rapid ranked games."""
        # Create an existing active rapid ranked game between user_a and user_b
        existing_game = GameService.create_game(
            self.deck_a,
            self.deck_b,
            randomize_starting_player=False,
        )
        existing_game.type = Game.GAME_TYPE_RANKED
        existing_game.ladder_type = Game.LADDER_TYPE_RAPID
        existing_game.status = Game.GAME_STATUS_IN_PROGRESS
        existing_game.save()

        # Queue both users for rapid ranked matchmaking with DIFFERENT decks
        # (same deck matchup would be caught by create_game's duplicate check)
        queue_a = MatchmakingQueue.objects.create(
            user=self.user_a,
            deck=self.deck_a2,  # Use alternate deck
            elo_rating=1500,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_RAPID,
        )
        queue_b = MatchmakingQueue.objects.create(
            user=self.user_b,
            deck=self.deck_b2,  # Use alternate deck
            elo_rating=1500,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_RAPID,
        )

        # Process matchmaking for rapid ladder
        matches_created = GameService.process_matchmaking(
            self.title.id,
            ladder_type=Game.LADDER_TYPE_RAPID
        )

        # Verify that a new match WAS created (rapid allows duplicates)
        self.assertEqual(matches_created, 1)

        # Verify that both queue entries are now MATCHED
        queue_a.refresh_from_db()
        queue_b.refresh_from_db()
        self.assertEqual(queue_a.status, MatchmakingQueue.STATUS_MATCHED)
        self.assertEqual(queue_b.status, MatchmakingQueue.STATUS_MATCHED)

        # Verify 2 games exist (the original + the new match)
        game_count = Game.objects.filter(
            type=Game.GAME_TYPE_RANKED,
            ladder_type=Game.LADDER_TYPE_RAPID,
        ).count()
        self.assertEqual(game_count, 2)

    def test_allow_new_daily_game_after_previous_completes(self):
        """Test that players can be matched again after their previous daily game completes."""
        # Create a COMPLETED daily ranked game between user_a and user_b
        completed_game = GameService.create_game(
            self.deck_a,
            self.deck_b,
            randomize_starting_player=False,
        )
        completed_game.type = Game.GAME_TYPE_RANKED
        completed_game.ladder_type = Game.LADDER_TYPE_DAILY
        completed_game.status = Game.GAME_STATUS_ENDED  # Game is completed
        completed_game.save()

        # Queue both users for daily ranked matchmaking
        queue_a = MatchmakingQueue.objects.create(
            user=self.user_a,
            deck=self.deck_a,
            elo_rating=1500,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_DAILY,
        )
        queue_b = MatchmakingQueue.objects.create(
            user=self.user_b,
            deck=self.deck_b,
            elo_rating=1500,
            status=MatchmakingQueue.STATUS_QUEUED,
            ladder_type=Game.LADDER_TYPE_DAILY,
        )

        # Process matchmaking for daily ladder
        matches_created = GameService.process_matchmaking(
            self.title.id,
            ladder_type=Game.LADDER_TYPE_DAILY
        )

        # Verify that a new match WAS created (previous game is completed)
        self.assertEqual(matches_created, 1)

        # Verify that both queue entries are now MATCHED
        queue_a.refresh_from_db()
        queue_b.refresh_from_db()
        self.assertEqual(queue_a.status, MatchmakingQueue.STATUS_MATCHED)
        self.assertEqual(queue_b.status, MatchmakingQueue.STATUS_MATCHED)

        # Verify 2 games exist (the completed + the new one)
        game_count = Game.objects.filter(
            type=Game.GAME_TYPE_RANKED,
            ladder_type=Game.LADDER_TYPE_DAILY,
        ).count()
        self.assertEqual(game_count, 2)


class RankedGameAbortTests(TestCase):
    """Tests for ranked game abort functionality when side_a times out on turn 1."""

    def setUp(self):
        """Create test users, title, decks for abort tests."""
        from django.utils import timezone
        from datetime import timedelta

        # Create two users
        self.user_a = User.objects.create_user(
            email="abort_user_a@example.com",
            username="abort_user_a"
        )
        self.user_b = User.objects.create_user(
            email="abort_user_b@example.com",
            username="abort_user_b"
        )

        # Create title and heroes
        self.title = Title.objects.create(slug='abort-test-title', author=self.user_a)
        self.hero_a = HeroTemplate.objects.create(
            title=self.title,
            slug='abort-hero-a',
            name="Hero A",
            health=30
        )
        self.hero_b = HeroTemplate.objects.create(
            title=self.title,
            slug='abort-hero-b',
            name="Hero B",
            health=30
        )

        # Create decks for both users
        self.deck_a = Deck.objects.create(
            title=self.title,
            user=self.user_a,
            name="Abort Deck A",
            hero=self.hero_a
        )
        self.deck_b = Deck.objects.create(
            title=self.title,
            user=self.user_b,
            name="Abort Deck B",
            hero=self.hero_b
        )

        # Add some cards to both decks
        for i in range(4):
            card = CardTemplate.objects.create(
                title=self.title,
                slug=f'abort-card-{i}',
                name=f'Abort Card {i}',
                cost=1,
            )
            DeckCard.objects.create(deck=self.deck_a, card=card)
            DeckCard.objects.create(deck=self.deck_b, card=card)

    def test_ranked_game_aborted_when_side_a_times_out_turn_1(self):
        """Test that a ranked game is marked aborted when side_a times out on turn 1."""
        from django.utils import timezone
        from datetime import timedelta
        from apps.gameplay.models import ELORatingChange

        # Create a ranked game
        game = GameService.create_game(
            self.deck_a,
            self.deck_b,
            randomize_starting_player=False,
        )
        game.type = Game.GAME_TYPE_RANKED
        game.ladder_type = Game.LADDER_TYPE_DAILY

        # Simulate game being in progress on turn 1, side_a's turn, main phase
        game.status = Game.GAME_STATUS_IN_PROGRESS
        game_state = game.game_state
        game_state.turn = 1
        game_state.active = 'side_a'
        game_state.phase = 'main'
        game_state.time_per_turn = 60
        game.state = game_state.model_dump()

        # Set turn as already expired
        game.turn_expires = timezone.now() - timedelta(seconds=10)
        game.save()

        # Run the expired turns check
        GameService.check_expired_turns()

        # Refresh the game from DB
        game.refresh_from_db()

        # Verify the game status is ABORTED (not ENDED)
        self.assertEqual(game.status, Game.GAME_STATUS_ABORTED)

        # Verify no winner was set
        self.assertIsNone(game.winner)

        # Verify no ELO change record was created
        self.assertFalse(ELORatingChange.objects.filter(game=game).exists())

    def test_ranked_game_not_aborted_when_side_b_times_out_turn_1(self):
        """Test that a ranked game is NOT aborted when side_b times out on turn 1."""
        from django.utils import timezone
        from datetime import timedelta
        from apps.gameplay.models import ELORatingChange

        # Create a ranked game
        game = GameService.create_game(
            self.deck_a,
            self.deck_b,
            randomize_starting_player=False,
        )
        game.type = Game.GAME_TYPE_RANKED
        game.ladder_type = Game.LADDER_TYPE_DAILY

        # Simulate game being in progress on turn 1, side_b's turn (after side_a ended turn)
        game.status = Game.GAME_STATUS_IN_PROGRESS
        game_state = game.game_state
        game_state.turn = 1
        game_state.active = 'side_b'
        game_state.phase = 'main'
        game_state.time_per_turn = 60
        game.state = game_state.model_dump()

        # Set turn as already expired
        game.turn_expires = timezone.now() - timedelta(seconds=10)
        game.save()

        # Run the expired turns check
        GameService.check_expired_turns()

        # Refresh the game from DB
        game.refresh_from_db()

        # Verify the game ended normally (not aborted)
        self.assertEqual(game.status, Game.GAME_STATUS_ENDED)

        # Verify ELO change record WAS created (normal game)
        self.assertTrue(ELORatingChange.objects.filter(game=game).exists())

    def test_ranked_game_not_aborted_on_turn_2(self):
        """Test that a ranked game is NOT aborted when side_a times out on turn 2+."""
        from django.utils import timezone
        from datetime import timedelta
        from apps.gameplay.models import ELORatingChange

        # Create a ranked game
        game = GameService.create_game(
            self.deck_a,
            self.deck_b,
            randomize_starting_player=False,
        )
        game.type = Game.GAME_TYPE_RANKED
        game.ladder_type = Game.LADDER_TYPE_DAILY

        # Simulate game being in progress on turn 2, side_a's turn
        game.status = Game.GAME_STATUS_IN_PROGRESS
        game_state = game.game_state
        game_state.turn = 2
        game_state.active = 'side_a'
        game_state.phase = 'main'
        game_state.time_per_turn = 60
        game.state = game_state.model_dump()

        # Set turn as already expired
        game.turn_expires = timezone.now() - timedelta(seconds=10)
        game.save()

        # Run the expired turns check
        GameService.check_expired_turns()

        # Refresh the game from DB
        game.refresh_from_db()

        # Verify the game ended normally (not aborted)
        self.assertEqual(game.status, Game.GAME_STATUS_ENDED)

        # Verify ELO change record WAS created (normal game)
        self.assertTrue(ELORatingChange.objects.filter(game=game).exists())

    def test_friendly_game_not_aborted(self):
        """Test that friendly games are never aborted (they just end normally on timeout)."""
        from django.utils import timezone
        from datetime import timedelta
        from apps.gameplay.models import ELORatingChange

        # Create a friendly game
        game = GameService.create_game(
            self.deck_a,
            self.deck_b,
            randomize_starting_player=False,
        )
        game.type = Game.GAME_TYPE_FRIENDLY

        # Simulate game being in progress on turn 1, side_a's turn
        game.status = Game.GAME_STATUS_IN_PROGRESS
        game_state = game.game_state
        game_state.turn = 1
        game_state.active = 'side_a'
        game_state.phase = 'main'
        game_state.time_per_turn = 60
        game.state = game_state.model_dump()

        # Set turn as already expired
        game.turn_expires = timezone.now() - timedelta(seconds=10)
        game.save()

        # Run the expired turns check
        GameService.check_expired_turns()

        # Refresh the game from DB
        game.refresh_from_db()

        # Verify the game ended normally (friendly games don't get aborted, just end)
        self.assertEqual(game.status, Game.GAME_STATUS_ENDED)

        # Verify no ELO change for friendly games regardless
        self.assertFalse(ELORatingChange.objects.filter(game=game).exists())

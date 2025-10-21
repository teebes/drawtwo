"""
Base test classes and shared fixtures for gameplay tests.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.builder.models import AIPlayer, CardTemplate, HeroTemplate, Title
from apps.builder.schemas import HeroPower, DamageAction
from apps.collection.models import Deck, DeckCard
from apps.gameplay.schemas.game import GameState, HeroInPlay
from apps.gameplay.services import GameService

User = get_user_model()


class ServiceTestsBase(TestCase):
    """Base class for tests that need a complete game with decks."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            username="testuser"
        )
        self.ai_player = AIPlayer.objects.create(name='AI')

        self.title = Title.objects.create(slug='title', author=self.user)

        self.hero_a = HeroTemplate.objects.create(
            title=self.title, slug='hero-a', name="Hero A", health=10)
        self.hero_b = HeroTemplate.objects.create(
            title=self.title, slug='hero-b', name="Hero B", health=10)
        self.deck_a = Deck.objects.create(
            title=self.title, user=self.user, name="Deck A", hero=self.hero_a)
        self.deck_b = Deck.objects.create(
            title=self.title, ai_player=self.ai_player, name="Deck B", hero=self.hero_b)

        for i in range(0, 4):
            card = CardTemplate.objects.create(
                title=self.title,
                slug='card-%s' % i,
                name='Card %s' % i,
                cost=1,
            )
            DeckCard.objects.create(deck=self.deck_a, card=card)
            DeckCard.objects.create(deck=self.deck_b, card=card)

        self.game = GameService.start_game(self.deck_a, self.deck_b)
        self.game.refresh_from_db()


class GamePlayTestBase(TestCase):
    """Base class for tests that need a simple game state."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.game_state = GameState(
            turn=1,
            active="side_a",
            phase="start",
            queue=[],
            event_queue=[],
            cards={},
            creatures={},
            last_creature_id=0,
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
                    hero_power=HeroPower(
                        actions=[
                            DamageAction(
                                amount=1,
                                target="enemy",
                            )
                        ]
                    ),
                ),
                'side_b': HeroInPlay(
                    hero_id="2",
                    template_slug="hero_b",
                    health=10,
                    name="Hero B",
                    hero_power=HeroPower(
                        actions=[
                            DamageAction(
                                amount=1,
                                target="enemy",
                            )
                        ]
                    ),
                ),
            },
        )

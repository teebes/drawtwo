import random

from django.db import transaction

from .models import Game
from .schemas import GameState, CardInPlay, HeroInPlay
from .tasks import process_player_action
from apps.core.serializers import serialize_cards_with_traits


class GameService:

    @staticmethod
    @transaction.atomic
    def start_game(deck_a, deck_b) -> Game:

        existing_game = Game.objects.filter(
            side_a=deck_a,
            side_b=deck_b,
        ).exclude(
            status=Game.GAME_STATUS_ENDED,
        ).first()
        if existing_game:
            return existing_game

        cards_a = serialize_cards_with_traits(deck_a.cards.all())
        cards_b = serialize_cards_with_traits(deck_b.cards.all())

        card_id = 0
        cards_in_play = {}
        decks = {'side_a': [], 'side_b': []}

        for card in cards_a:
            card_id += 1
            cards_in_play[card_id] = CardInPlay(
                card_id=card_id,
                template_slug=card["slug"],
                attack=card["attack"],
                health=card["health"],
                cost=card["cost"],
                traits=card["traits"],
            )
            decks['side_a'].append(card_id)

        for card in cards_b:
            card_id += 1
            cards_in_play[card_id] = CardInPlay(
                card_id=card_id,
                template_slug=card["slug"],
                attack=card["attack"],
                health=card["health"],
                cost=card["cost"],
                traits=card["traits"],
            )
            decks['side_b'].append(card_id)

        # shuffle both decks
        random.shuffle(decks['side_a'])
        random.shuffle(decks['side_b'])

        heroes = {
            'side_a': HeroInPlay(
                hero_id=deck_a.hero.id,
                template_slug=deck_a.hero.slug,
                health=deck_a.hero.health,
                name=deck_a.hero.name,
            ),
            'side_b': HeroInPlay(
                hero_id=deck_b.hero.id,
                template_slug=deck_b.hero.slug,
                health=deck_b.hero.health,
                name=deck_b.hero.name,
            ),
        }

        game_state = GameState(
            turn=1,
            active='side_a',
            phase='start',
            event_queue=[],
            cards=cards_in_play,
            heroes=heroes,
            decks=decks,
        )

        game = Game.objects.create(
            status=Game.GAME_STATUS_INIT,
            side_a=deck_a,
            side_b=deck_b,
            state=game_state.model_dump(),
        )

        return game

    @staticmethod
    def submit_action(game_id: int, action: dict):
        process_player_action.delay(game_id, action)

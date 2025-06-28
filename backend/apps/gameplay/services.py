import random

from django.db import transaction
from typing import List

from .models import Game
from .schemas import (
    CardInPlay,
    GameState,
    GameUpdate,
    HeroInPlay,
    Event)
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

    def __init__(self, game: Game) -> None:
        self.game = game
        self.game_state = GameState.model_validate(game.state)

    def queue_events(self, events: List[Event]) -> None:
        for event in events:
            self.game_state.event_queue.append(event)
        self.game.state = self.game_state.model_dump()
        self.game.save()

    def process_events(self) -> List[GameUpdate]:
        events = self.game_state.event_queue
        changes = []
        for event in events:
            if event.type == "draw_card":
                changes.extend(self.draw_card(self.game_state, event.player))
            else:
                raise ValueError(f"Invalid event: {event.type}")

        self.game_state.event_queue = []
        self.game.state = self.game_state.model_dump()
        self.game.save()

        return changes


    @staticmethod
    def draw_card(game_state: GameState, side: str) -> List[GameUpdate]:
        try:
            deck = game_state.decks[side]
        except KeyError:
            raise ValueError(f"Invalid side: {side}")

        if not deck:
            raise ValueError(f"No cards left in deck for {side}")

        # Remove the card from the deck
        card_id = deck.pop(0)

        # Add the card to the hand
        game_state.hands[side].append(card_id)

        return [
            GameUpdate(
                type="draw_card",
                side=side,
                data={
                    "card": game_state.cards[card_id].model_dump(),
                },
            )
        ]

    # play_card

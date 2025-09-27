import random

from django.db import transaction
from pydantic import TypeAdapter

from .models import Game
from .schemas import (
    CardInPlay,
    EndTurnAction,
    EndTurnEvent,
    GameAction,
    GameState,
    HeroInPlay,
    PlayCardAction,
    PlayCardEvent,
    StartGameEvent,
    UseCardAction,
    UseCardEvent,
)

from .tasks import step
from apps.builder.schemas import TitleConfig
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

        deck_a_card_copies = {
            card_copy.card.id: card_copy.count
            for card_copy in deck_a.deckcard_set.all()
        }
        deck_b_card_copies = {
            card_copy.card.id: card_copy.count
            for card_copy in deck_b.deckcard_set.all()
        }

        cards_a = serialize_cards_with_traits(deck_a.cards.all())
        cards_b = serialize_cards_with_traits(deck_b.cards.all())

        card_id = 0
        cards_in_play = {}
        decks = {'side_a': [], 'side_b': []}

        for card in cards_a:

            for _ in range(deck_a_card_copies[card["id"]]):

                card_id += 1
                cards_in_play[str(card_id)] = CardInPlay(
                    card_type=card["card_type"],
                    card_id=str(card_id),
                    template_slug=card["slug"],
                    name=card["name"],
                    description=card["description"],
                    attack=card["attack"],
                    health=card["health"],
                    cost=card["cost"],
                    traits=card["traits"],
                )
                decks['side_a'].append(str(card_id))

        for card in cards_b:

            for _ in range(deck_b_card_copies[card["id"]]):

                card_id += 1
                cards_in_play[str(card_id)] = CardInPlay(
                    card_type=card["card_type"],
                    card_id=str(card_id),
                    template_slug=card["slug"],
                    name=card["name"],
                    description=card["description"],
                    attack=card["attack"],
                    health=card["health"],
                    cost=card["cost"],
                    traits=card["traits"],
                )
                decks['side_b'].append(str(card_id))

        # shuffle both decks
        random.shuffle(decks['side_a'])
        random.shuffle(decks['side_b'])

        heroes = {
            'side_a': HeroInPlay(
                hero_id=str(deck_a.hero.id),
                template_slug=deck_a.hero.slug,
                health=deck_a.hero.health,
                name=deck_a.hero.name,
            ),
            'side_b': HeroInPlay(
                hero_id=str(deck_b.hero.id),
                template_slug=deck_b.hero.slug,
                health=deck_b.hero.health,
                name=deck_b.hero.name,
            ),
        }

        ai_sides = []
        if deck_a.is_ai_deck:
            ai_sides.append('side_a')
        if deck_b.is_ai_deck:
            ai_sides.append('side_b')

        config = TitleConfig.model_validate(deck_a.title.config)

        game_state = GameState(
            turn=1,
            active='side_a',
            phase='start',
            event_queue=[
                StartGameEvent(side='side_a'),
            ],
            cards=cards_in_play,
            heroes=heroes,
            decks=decks,
            ai_sides=ai_sides,
            config=config,
        )

        game = Game.objects.create(
            status=Game.GAME_STATUS_INIT,
            side_a=deck_a,
            side_b=deck_b,
            state=game_state.model_dump(),
        )

        step.apply_async(args=[game.id])

        return game

    @staticmethod
    def submit_action(game_id: int, action: dict):
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            raise ValueError(f"Game with id {game_id} does not exist")

        game_state = GameState.model_validate(game.state)

        if game_state.phase != "main": return

        game_action = TypeAdapter(GameAction).validate_python(action)
        print('game_action ----> ', game_action)

        if isinstance(game_action, PlayCardAction):
            print('game_action.card_id is %s' % game_action.card_id)
            play_card_event = PlayCardEvent(
                side=game_state.active,
                card_id=game_action.card_id,
                position=game_action.position,
                target_type=game_action.target_type,
                target_id=game_action.target_id,
            )
            print(play_card_event)
            game_state.event_queue.append(play_card_event)
        elif isinstance(game_action, EndTurnAction):
            game_state.event_queue.append(EndTurnEvent(
                side=game_state.active,
            ))
        elif isinstance(game_action, UseCardAction):
            game_state.event_queue.append(UseCardEvent(
                side=game_state.active,
                card_id=game_action.card_id,
                target_type=game_action.target_type,
                target_id=game_action.target_id,
            ))

        else:
            raise ValueError(f"Invalid action: {game_action}")

        game.state = game_state.model_dump()
        game.save(update_fields=["state"])
        step.apply_async(args=[game_id])

    def __init__(self, game: Game) -> None:
        self.game = game
        self.game_state = GameState.model_validate(game.state)

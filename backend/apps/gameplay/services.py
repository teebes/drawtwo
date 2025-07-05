from os import SCHED_IDLE
import random

from django.db import transaction
from typing import List

from .models import Game
from .schemas import (
    Action,
    CardInPlay,
    DrawEvent,
    DrawUpdate,
    NewTurnEvent,
    NewTurnUpdate,
    Event,
    EventType,
    GameState,
    GameUpdate,
    ManaUpdate,
    HeroInPlay,
    PHASE_ORDER,
    PhaseTransitionAction,
    PlayAction,
    PlayEvent,
    PlayUpdate,
    RefreshEvent,
    StartTurnEvent,
    UpdateType)
from .tasks import process_ai_action
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
            cards_in_play[str(card_id)] = CardInPlay(
                card_id=card_id,
                template_slug=card["slug"],
                attack=card["attack"],
                health=card["health"],
                cost=card["cost"],
                traits=card["traits"],
            )
            decks['side_a'].append(str(card_id))

        for card in cards_b:
            card_id += 1
            cards_in_play[str(card_id)] = CardInPlay(
                card_id=card_id,
                template_slug=card["slug"],
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
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            raise ValueError(f"Game with id {game_id} does not exist")

        updates = []

        service = GameService(game)
        if action['type'] == 'phase_transition':
            updates = service.process_phase_transition(
                PhaseTransitionAction.model_validate(action))
        elif action['type'] == 'play':
            updates = service.process_action(PlayAction.model_validate(action))
        else:
            raise ValueError(f"Invalid action: {action['type']}")

        if (service.game.state['phase'] == "start"
            and
            getattr(service.game, service.game.state['active']).is_ai_deck):
            # Queue AI process
            process_ai_action.delay(game_id)

        return {
            "updates": [update.model_dump() for update in updates],
            "state": service.game.state,
        }

    def __init__(self, game: Game) -> None:
        self.game = game
        self.game_state = GameState.model_validate(game.state)

    def process_phase_transition(self, action: PhaseTransitionAction) -> List[UpdateType]:
        current_phase = self.game_state.phase
        target_phase = action.phase
        # See whether the transition is allowed based on the phase order, target phase
        # and current phase.
        if target_phase not in PHASE_ORDER:
            raise ValueError(f"Invalid phase: {target_phase}")
        if ((PHASE_ORDER.index(target_phase) != PHASE_ORDER.index(current_phase) + 1)
            and not (current_phase == "main" and target_phase == "start")):
            raise ValueError(
                f"Invalid phase transition: {current_phase} -> {target_phase}")

        if target_phase == "refresh":
            self.queue_events([RefreshEvent(side=self.game_state.active)])
        elif target_phase == "draw":
            self.queue_events([DrawEvent(side=self.game_state.active)])
        elif target_phase == "start":
            self.queue_events([NewTurnEvent(side=self.game_state.active)])

        self.game_state.phase = target_phase

        return self.process_events()

    def process_action(self, action: PlayAction) -> List[UpdateType]:
        if action.type == "play":
            self.queue_events([PlayEvent(
                side=self.game_state.active,
                card_id=action.card_id,
                position=action.position)])
        else:
            raise ValueError(f"Invalid action: {action.type}")

        return self.process_events()

    def queue_events(self, events: List[EventType]) -> None:
        for event in events:
            self.game_state.event_queue.append(event)
        self.game.state = self.game_state.model_dump()
        self.game.save()

    def process_events(self) -> List[UpdateType]:
        events = self.game_state.event_queue
        changes = []
        for event in events:

            if event.type == "draw_card":
                changes.extend(self.draw_card(self.game_state, event.side))

            elif event.type == "refresh":
                changes.extend(self.refresh(self.game_state, event.side))

            elif event.type == "play":
                changes.extend(self.play_card(
                    game_state=self.game_state,
                    side=event.side,
                    card_id=event.card_id,
                    position=event.position))

            elif event.type == "new_turn":
                changes.extend(self.new_turn(
                    game_state=self.game_state,
                    side=event.side
                ))

            else:
                raise ValueError(f"Invalid event: {event.type}")

        self.game_state.event_queue = []
        self.game.state = self.game_state.model_dump()
        self.game.save()

        return changes

    @staticmethod
    def refresh(game_state: GameState, side: str) -> List[UpdateType]:
        game_state.mana_used[side] = 0
        game_state.mana_pool[side] = game_state.turn
        for card_on_board in game_state.board[side]:
            game_state.cards[card_on_board].exhausted = False
        return [
            ManaUpdate(
                type="mana",
                side=side,
                data={
                    "mana_pool": game_state.mana_pool[side],
                    "mana_used": game_state.mana_used[side],
                },
            )
        ]

    @staticmethod
    def draw_card(game_state: GameState, side: str) -> List[UpdateType]:
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
            DrawUpdate(
                type="draw",
                side=side,
                data={
                    "card": game_state.cards[card_id].model_dump(),
                },
            )
        ]

    @staticmethod
    def play_card(game_state: GameState, side: str, card_id: str, position: int):
        game_state.hands[side].remove(card_id)
        game_state.board[side].insert(position, card_id)
        game_state.mana_used[side] += game_state.cards[card_id].cost
        return [
            PlayUpdate(
                type="play",
                side=side,
                card_id=card_id,
                position=position,
                data={},
            )
        ]

    @staticmethod
    def new_turn(game_state: GameState, side: str) -> List[UpdateType]:
        if game_state.active == "side_b":
            game_state.active = "side_a"
            game_state.turn += 1
        else:
            game_state.active = "side_b"
        return [NewTurnUpdate(side=side)]
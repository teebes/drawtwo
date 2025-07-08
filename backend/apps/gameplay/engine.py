"""
Gameplay engine to process events. Each function takes 1 event
and returns:
* the new state (without modifying the initial state)
* updates
* events
"""

from pydantic import BaseModel

from .schemas import GameState, Phase
from .schemas import (
    DrawPhaseEvent,
    DrawPhaseUpdate,
    EndTurnEvent,
    EndTurnUpdate,
    GameEvent,
    GameUpdate,
    MainPhaseEvent,
    MainPhaseUpdate,
    PlayCardEvent,
    PlayCardUpdate,
    RefreshPhaseEvent,
    RefreshPhaseUpdate,
    ResolvedEvent)


class HandledEvent(BaseModel):
    events: list[GameEvent]
    updates: list[GameUpdate]


def resolve_event(state: GameState) -> ResolvedEvent:
    """
    Resolve an event and return the updated state, any new events to process,
    and any updates to send to the client.
    """

    event = state.event_queue.pop(0)

    events = []
    updates = []
    # The new state will be mutated by the handlers
    new_state: GameState = state.model_copy(deep=True)

    if isinstance(event, RefreshPhaseEvent):
        events, updates = handle_refresh_phase(new_state, event)

    elif isinstance(event, DrawPhaseEvent):
        events, updates = handle_draw_phase(new_state, event)

    elif isinstance(event, MainPhaseEvent):
        events, updates = handle_main_phase(new_state, event)

    elif isinstance(event, EndTurnEvent):
        events, updates = handle_end_turn(new_state, event)

    elif isinstance(event, PlayCardEvent):
        events, updates = handle_play_card(new_state, event)

    else:
        raise ValueError(f"Invalid event: {event}")

    new_state.event_queue.extend(events)

    return ResolvedEvent(
        state=new_state,
        events=events,
        updates=updates
    )


def handle_refresh_phase(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    state.phase = "refresh"
    state.mana_pool[event.side] = state.turn
    state.mana_used[event.side] = 0
    for card_on_board in state.board[event.side]:
        state.cards[card_on_board].exhausted = False
    events = [DrawPhaseEvent(side=event.side)]
    updates = [RefreshPhaseUpdate(side=state.active)]
    return events, updates


def handle_draw_phase(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    state.phase = "draw"
    deck = state.decks[event.side]
    card_id = deck.pop(0)
    state.hands[event.side].append(card_id)
    events = [MainPhaseEvent(side=event.side)]
    updates = [DrawPhaseUpdate(side=event.side)]
    return events, updates


def handle_main_phase(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    state.phase = "main"
    events = []
    updates = [MainPhaseUpdate(side=event.side)]
    return events, updates


def handle_end_turn(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    state.active = "side_b" if state.active == "side_a" else "side_a"
    if state.active == "side_a":
        state.turn += 1
    state.phase = "start"
    events = [RefreshPhaseEvent(side=state.active)]
    updates = [EndTurnUpdate(side=state.active)]
    return events, updates


def handle_play_card(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    state.hands[event.side].remove(event.card_id)
    state.board[event.side].insert(event.position, event.card_id)
    state.mana_used[event.side] += state.cards[event.card_id].cost
    events = []
    updates = [
        PlayCardUpdate(side=event.side, card_id=event.card_id, position=event.position)
    ]
    return events, updates


def determine_ai_move(state: GameState) -> GameEvent:
    # Start by seeing if there's a card that can be played from hand to board
    mana_pool = state.mana_pool[state.active]
    mana_used = state.mana_used[state.active]
    mana_available = mana_pool - mana_used

    for card_id in state.hands[state.active]:
        card = state.cards[card_id]
        if card.cost <= mana_available:
            card_id_to_play = card_id
            return PlayCardEvent(
                side=state.active,
                card_id=card_id_to_play,
                position=0)

    return EndTurnEvent(side=state.active)


"""
def apply_action(state_dict: dict, action: dict) -> dict:
    state = GameState.model_validate(state_dict)
    queue:list[Event] = list(state.event_queue)
    queue.append(Event(**action))

    emitted: list[Event] = []

    while queue:
        evt = queue.pop(0)
        emitted.append(evt)
        state, new_evts = resolve(evt, state)
        queue.extend(new_evts)

    state.event_queue = []
    return state.model_dump_json()
"""
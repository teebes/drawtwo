"""
Gameplay engine to process events. Each function takes 1 event
and returns:
* the new state (without modifying the initial state)
* updates
* events
"""

from pydantic import BaseModel

from .schemas import (
    CardDamageUpdate,
    CardDestroyedUpdate,
    CardRetaliationEvent,
    DrawPhaseEvent,
    DrawPhaseUpdate,
    EndTurnEvent,
    EndTurnUpdate,
    GameState,
    GameEvent,
    GameOverUpdate,
    GameUpdate,
    HeroDamageUpdate,
    MainPhaseEvent,
    MainPhaseUpdate,
    Phase,
    PlayCardEvent,
    PlayCardUpdate,
    RefreshPhaseEvent,
    RefreshPhaseUpdate,
    ResolvedEvent,
    UseCardEvent)


class HandledEvent(BaseModel):
    events: list[GameEvent]
    updates: list[GameUpdate]


def resolve_event(state: GameState) -> ResolvedEvent:
    """
    Resolve an event and return the updated state, any new events to process,
    and any updates to send to the client.
    """

    event = state.event_queue.pop(0)

    print('=========================')
    print(f"Resolving event: {event}")
    print('')

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

    elif isinstance(event, UseCardEvent):
        events, updates = handle_use_card(new_state, event)

    elif isinstance(event, CardRetaliationEvent):
        events, updates = handle_card_retaliation(new_state, event)

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


def handle_use_card(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    source_card_id = event.card_id
    source_card = state.cards[source_card_id]
    target_type = event.target_type

    opposing_side = "side_b" if event.side == "side_a" else "side_a"

    if target_type == "hero":
        hero = state.heroes[opposing_side]
        hero.health -= source_card.attack
        if hero.health <= 0:
            # If the hero dies, that is a game over event
            state.winner = event.side
            return [], [GameOverUpdate(side=event.side, winner=event.side)]
        else:
            return [], [HeroDamageUpdate(
                            side=event.side,
                            hero_id=hero.hero_id,
                            damage=hero.health)]

    # type is card
    target_card_id = event.target_id
    card = state.cards[target_card_id]
    card.health -= source_card.attack
    if card.health <= 0:
        state.board[opposing_side].remove(target_card_id)
        # TODO: put deathrattle mechanism here
        return [], [CardDestroyedUpdate(side=event.side, card_id=target_card_id)]
    else:
        events = [CardRetaliationEvent(
                    side=event.side,
                    card_id=target_card_id,
                    target_id=source_card_id)]
        changes = [CardDamageUpdate(
                        side=event.side,
                        card_id=target_card_id,
                        damage=source_card.attack)]
        return events, changes


def handle_card_retaliation(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    source_card_id = event.card_id
    source_card = state.cards[source_card_id]
    target_card_id = event.target_id
    target_card = state.cards[target_card_id]
    target_card.health -= source_card.attack
    if target_card.health <= 0:
        state.board[event.side].remove(target_card_id)
        return [], [CardDestroyedUpdate(side=event.side, card_id=target_card_id)]
    else:
        return [], [CardDamageUpdate(
                        side=event.side,
                        card_id=target_card_id,
                        damage=source_card.attack)]


def determine_ai_move(state: GameState) -> GameEvent:
    # Start by seeing if there's a card that can be played from hand to board
    mana_pool = state.mana_pool[state.active]
    mana_used = state.mana_used[state.active]
    mana_available = mana_pool - mana_used

    for card_id in state.hands[state.active]:
        card = state.cards[card_id]
        if card.cost <= mana_available and card.card_type == 'minion':
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
from .schemas import GameState, Event


def resolve(event: Event, state: GameState) -> tuple[GameState, list[Event]]:
    """
    Resolve an event and return the updated state and any new events to process.
    """
    new_events = []

    print(f"Resolving event: {event.type} - Current phase: {state.phase}")

    if event.type == 'phase_transition':
        # Handle phase transitions
        new_phase = event.data.get('phase') if event.data else None
        print(f"Phase transition from {state.phase} to {new_phase}")

        if new_phase == 'draw':
            state.phase = 'draw'
            print(f"Phase changed to: {state.phase}")
            # When transitioning to draw phase, create a draw event
            draw_event = Event(
                type='draw_card',
                player=state.active,
                data={}
            )
            new_events.append(draw_event)

    elif event.type == 'draw_card':
        # Handle drawing a card
        player = event.player
        print(f"Drawing card for {player}")
        if state.decks[player]:
            # Move top card from deck to hand
            card_id = state.decks[player].pop(0)
            state.hands[player].append(card_id)
            print(f"Card {card_id} drawn for {player}")

    # Return updated state and any new events
    return state, new_events


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
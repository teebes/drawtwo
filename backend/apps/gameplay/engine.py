from .schemas import GameState, Event


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
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
    ChooseAIMoveEvent,
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
    PlayCardEvent,
    PlayCardUpdate,
    RefreshPhaseEvent,
    RefreshPhaseUpdate,
    ResolvedEvent,
    UseCardEvent,
    CardInPlay,
    Trait,)


class HandledEvent(BaseModel):
    events: list[GameEvent]
    updates: list[GameUpdate]


# ==== Trait System ====

def get_cards_for_event(state: GameState, event: GameEvent) -> list[str]:
    """
    Return list of card IDs that should have their traits checked for this event.
    """
    cards_to_check = []

    if isinstance(event, PlayCardEvent):
        # Only check the card that was just played
        cards_to_check = [event.card_id]

    elif isinstance(event, UseCardEvent):
        # Check the attacking card and potentially the target card
        cards_to_check = [event.card_id]
        if event.target_type == "card":
            cards_to_check.append(event.target_id)

    elif isinstance(event, CardRetaliationEvent):
        # Check the retaliating card
        cards_to_check = [event.card_id]

    elif isinstance(event, EndTurnEvent):
        # Check all cards on the board for the ending turn side
        cards_to_check = state.board[event.side].copy()

    elif isinstance(event, RefreshPhaseEvent):
        # Check all cards on the board for the refreshing side (turn start effects)
        cards_to_check = state.board[event.side].copy()

    elif isinstance(event, DrawPhaseEvent):
        # Check all cards on the board for draw-related triggers
        cards_to_check = state.board[event.side].copy()

    return cards_to_check


def handle_trait_effects(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    """Handle all trait effects for a given event"""
    events = []
    updates = []

    # Get relevant cards based on event type
    cards_to_check = get_cards_for_event(state, event)

    for card_id in cards_to_check:
        card = state.cards[card_id]
        for trait in card.traits:
            if trait.slug in TRAIT_HANDLERS:
                trait_events, trait_updates = TRAIT_HANDLERS[trait.slug](
                    state, event, card, trait
                )
                events.extend(trait_events)
                updates.extend(trait_updates)

    return events, updates


# Individual trait handlers

def handle_charge_trait(state: GameState, event: GameEvent, card: CardInPlay, trait: Trait) -> tuple[list[GameEvent], list[GameUpdate]]:
    """Charge: Can attack immediately when played"""
    if isinstance(event, PlayCardEvent) and event.card_id == card.card_id:
        card.exhausted = False
    return [], []


# TODO: Add other trait handlers here:
# def handle_deathrattle_trait(state: GameState, event: GameEvent, card: CardInPlay, trait: Trait):
#     """Deathrattle: Effect triggers when card is destroyed"""
#     # Implementation for deathrattle effects
#     return [], []
#
# def handle_taunt_trait(state: GameState, event: GameEvent, card: CardInPlay, trait: Trait):
#     """Taunt: Enemies must attack this card first"""
#     # Implementation for taunt mechanics
#     return [], []
#
# def handle_rush_trait(state: GameState, event: GameEvent, card: CardInPlay, trait: Trait):
#     """Rush: Can attack minions (but not heroes) immediately when played"""
#     # Implementation for rush mechanics
#     return [], []


# Registry of trait handlers
TRAIT_HANDLERS = {
    "charge": handle_charge_trait,
    # TODO: Add other traits here as they're implemented
    # "deathrattle": handle_deathrattle_trait,
    # "taunt": handle_taunt_trait,
    # "rush": handle_rush_trait,
}


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

    elif isinstance(event, ChooseAIMoveEvent):
        events, updates = handle_choose_ai_move(new_state, event)

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
    # for card_on_board in state.board[event.side]:
    #     state.cards[card_on_board].exhausted = False
    events = [DrawPhaseEvent(side=event.side)]
    updates = [RefreshPhaseUpdate(side=state.active)]
    return events, updates


def handle_draw_phase(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    state.phase = "draw"

    deck = state.decks[event.side]

    try:
        card_id = deck.pop(0)
    except IndexError:
        # No more cards in the deck
        opposing_side = "side_b" if event.side == "side_a" else "side_a"
        events = []
        updates = [GameOverUpdate(side=event.side, winner=opposing_side)]
        return events, updates

    state.hands[event.side].append(card_id)
    events = [MainPhaseEvent(side=event.side)]
    updates = [DrawPhaseUpdate(side=event.side)]
    return events, updates


def handle_main_phase(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    state.phase = "main"

    events = []

    # If the new active side is an AI, queue up a choose ai move event
    if event.side in state.ai_sides:
        events = [ChooseAIMoveEvent(side=event.side)]

    updates = [MainPhaseUpdate(side=event.side)]
    return events, updates


def handle_end_turn(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:

    for card_on_board in state.board[event.side]:
        state.cards[card_on_board].exhausted = False

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

    # Handle trait effects AFTER the card is played
    trait_events, trait_updates = handle_trait_effects(state, event)

    events = trait_events
    updates = [
        PlayCardUpdate(side=event.side, card_id=event.card_id, position=event.position)
    ] + trait_updates
    return events, updates


def handle_use_card(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    source_card_id = event.card_id
    source_card = state.cards[source_card_id]
    target_type = event.target_type

    opposing_side = "side_b" if event.side == "side_a" else "side_a"

    source_card.exhausted = True

    if target_type == "hero":
        hero = state.heroes[opposing_side]
        hero.health -= source_card.attack
        if hero.health <= 0:
            # If the hero dies, that is a game over event
            state.winner = event.side
            events = []
            #events = [GameOverEvent(winner=event.side)]
            updates = [GameOverUpdate(side=event.side, winner=event.side)]
            return events, updates
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


def handle_choose_ai_move(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    mana_pool = state.mana_pool[state.active]
    mana_used = state.mana_used[state.active]
    mana_available = mana_pool - mana_used

    opposing_side = "side_b" if state.active == "side_a" else "side_a"

    # See if there's a card that can be played from hand to board
    for card_id in state.hands[state.active]:
        card = state.cards[card_id]
        if card.cost <= mana_available and card.card_type == 'minion':
            card_id_to_play = card_id
            play_event = PlayCardEvent(
                side=state.active,
                card_id=card_id_to_play,
                position=0)
            choose_ai_move = ChooseAIMoveEvent(side=state.active)
            return [play_event, choose_ai_move], []

    # See if there's a card that can be used to attack, and if there is,
    # attack the hero.
    for card_id in state.board[state.active]:
        card = state.cards[card_id]
        if not card.exhausted:
            use_event = UseCardEvent(
                side=state.active,
                card_id=card_id,
                target_type="hero",
                target_id=state.heroes[opposing_side].hero_id)
            choose_ai_move = ChooseAIMoveEvent(side=state.active)
            return [use_event, choose_ai_move], []

    return [EndTurnEvent(side=state.active)], []


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
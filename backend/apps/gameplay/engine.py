"""
Gameplay engine to process events. Each function takes 1 event
and returns:
* the new state (without modifying the initial state)
* updates
* events
"""

import random
from typing import List

from pydantic import BaseModel, TypeAdapter

from apps.builder.schemas import (
    CardActionDraw,
    CardActionDamage,
    CardAction,
)

from apps.gameplay.schemas.events import (
    CardRetaliationEvent,
    ChooseAIMoveEvent,
    DealDamageEvent,
    DrawCardEvent,
    DrawPhaseEvent,
    EndTurnEvent,
    GameEvent,
    MainPhaseEvent,
    MinionAttackEvent,
    PlayCardEvent,
    RefreshPhaseEvent,
    StartGameEvent,
    UseCardEvent,
)

from .schemas import (
    CardDamageUpdate,
    CardDestroyedUpdate,
    DealDamageUpdate,
    DrawCardEvent,
    DrawCardUpdate,
    DrawPhaseUpdate,
    EndTurnUpdate,
    GameState,
    GameOverUpdate,
    GameUpdate,
    HeroDamageUpdate,
    MainPhaseUpdate,
    PlayCardUpdate,
    RefreshPhaseUpdate,
    ResolvedEvent,
    CardInPlay,
    Trait,)



# ==== Trait System ====

TRIGGER_MAP = {}
TRIGGER_MAP['update_play_card'] = ["charge", "battlecry"]

def apply_traits(state: GameState, update: GameUpdate) -> tuple[list[GameEvent], list[GameUpdate]]:
    events = []
    updates = []

    # Route the event to a trait handler based on the trigger map
    for update_type in TRIGGER_MAP:
        if update.type == update_type:
            card: CardInPlay = state.cards[update.card_id]
            for trait in state.cards[update.card_id].traits:
                if trait.type in TRIGGER_MAP[update_type]:
                    trait_events, trait_updates = TRAIT_HANDLERS[trait.type](
                        state, update, card, trait)
                    events.extend(trait_events)
                    updates.extend(trait_updates)

    return events, updates

def handle_card_actions(state: GameState, card: CardInPlay, trait: Trait) -> tuple[list[GameEvent], list[GameUpdate]]:
    events = []
    updates = []
    for card_action in trait.actions:
        _events, _updates = handle_card_action(state, card, card_action)
        events.extend(_events)
        updates.extend(_updates)
    return events, updates

def handle_card_action(state: GameState, card: CardInPlay, card_action: CardAction) -> tuple[list[GameEvent], list[GameUpdate]]:
    events = []
    updates = []

    if isinstance(card_action, CardActionDraw):
        events.append(DrawCardEvent(side=state.active, amount=card_action.amount))

    return events, updates

# Individual trait handlers

def handle_charge_trait(state: GameState, update: PlayCardUpdate, card: CardInPlay, trait: Trait) -> tuple[list[GameEvent], list[GameUpdate]]:
    """Charge: Can attack immediately when played"""
    card.exhausted = False
    return [], []

def handle_battlecry_trait(state: GameState, update: PlayCardUpdate, card: CardInPlay, trait: Trait) -> tuple[list[GameEvent], list[GameUpdate]]:
    """Battlecry: Effect triggers when card is played"""
    return handle_card_actions(state, card, trait)

def handle_deathrattle_trait(state: GameState, update: PlayCardUpdate, card: CardInPlay, trait: Trait) -> tuple[list[GameEvent], list[GameUpdate]]:
    """Deathrattle: Effect triggers when card is destroyed"""
    return handle_card_actions(state, card, trait)

# Registry of trait handlers
TRAIT_HANDLERS = {
    "charge": handle_charge_trait,
    "battlecry": handle_battlecry_trait,
    "deathrattle": handle_deathrattle_trait,
}

def translate_card_action(state: GameState, definition) -> list[GameEvent]:
    """
    Translate a card action definition into a list of events.
    """
    events = []
    return events


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

    if isinstance(event, StartGameEvent):
        events, updates = handle_start_game(new_state, event)

    elif isinstance(event, RefreshPhaseEvent):
        events, updates = handle_refresh_phase(new_state, event)

    elif isinstance(event, DrawPhaseEvent):
        events, updates = handle_draw_phase(new_state, event)

    elif isinstance(event, MainPhaseEvent):
        events, updates = handle_main_phase(new_state, event)

    elif isinstance(event, EndTurnEvent):
        events, updates = handle_end_turn(new_state, event)

    elif isinstance(event, DrawCardEvent):
        events, updates = handle_draw_card(new_state, event)

    elif isinstance(event, PlayCardEvent):
        events, updates = handle_play_card(new_state, event)

    elif isinstance(event, UseCardEvent):
        events, updates = handle_use_card(new_state, event)

    elif isinstance(event, MinionAttackEvent):
        events, updates = handle_minion_attack(new_state, event)

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


def handle_start_game(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    state.phase = "start"

    hand_size = state.config.hand_start_size
    if hand_size < 0: hand_size = 0

    events = []

    for _ in range(hand_size):
        events.append(DrawCardEvent(side=state.active))

    events.append(RefreshPhaseEvent(side=state.active))

    updates = []
    return events, updates


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
    events = [DrawCardEvent(side=event.side), MainPhaseEvent(side=event.side)]
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

    end_of_turn_active = state.active

    state.active = "side_b" if state.active == "side_a" else "side_a"
    if state.active == "side_a":
        state.turn += 1
    state.phase = "start"
    events = [RefreshPhaseEvent(side=state.active)]
    updates = [EndTurnUpdate(side=end_of_turn_active)]
    return events, updates

def handle_draw_card(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
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

    events = []
    updates = [DrawCardUpdate(side=event.side, card_id=card_id)]
    return events, updates

def handle_play_card(state: GameState, event: GameEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    state.hands[event.side].remove(event.card_id)
    state.board[event.side].insert(event.position, event.card_id)
    state.mana_used[event.side] += state.cards[event.card_id].cost

    events = []
    updates = []

    play_card_update = PlayCardUpdate(
        side=event.side,
        card_id=event.card_id,
        position=event.position)

    updates.append(play_card_update)

    trait_events, trait_updates = apply_traits(state, play_card_update)

    events.extend(trait_events)
    updates.extend(trait_updates)

    return events, updates


def handle_minion_attack(state: GameState, event: MinionAttackEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    source_card_id = event.card_id
    source_card = state.cards[source_card_id]
    target_type = event.target_type
    target_id = event.target_id

    source_card.exhausted = True

    damage_event = DealDamageEvent(
        source_type="card",
        source_id=source_card_id,
        target_type=target_type,
        target_id=target_id,
        damage=source_card.attack
    )

    return [damage_event], []

def handle_deal_damage(state: GameState, event: DealDamageEvent) -> tuple[list[GameEvent], list[GameUpdate]]:
    target_type = event.target_type

    opposing_side = "side_b" if event.side == "side_a" else "side_a"
    updates = [DealDamageUpdate(
        source_type=event.source_type,
        source_id=event.source_id,
        target_type=event.target_type,
        target_id=event.target_id,
        damage=event.damage
    )]

    if target_type == "hero":
        hero = state.heroes[opposing_side]
        hero.health -= event.damage
        if hero.health <= 0:
            # If the hero dies, that is a game over event
            state.winner = event.side
            updates.append(GameOverUpdate(side=event.side, winner=event.side))
        return [], updates

    # target is card
    target_card = state.cards[event.target_id]

    target_card.health -= event.damage
    if target_card.health <= 0:
        state.board[opposing_side].remove(event.target_id)
        # TODO: put deathrattle mechanism here
        return [], [CardDestroyedUpdate(side=event.side, card_id=event.target_id)]
    else:
        events = [CardRetaliationEvent(
                    side=event.side,
                    card_id=event.target_id,
                    target_id=source_card_id)]
        changes = [CardDamageUpdate(
                        side=event.side,
                        card_id=target_card_id,
                        damage=source_card.attack)]
        return events, changes

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
            # 50/50 chance to attack hero or card
            if random.random() < 0.5:
                target_type = "hero"
                target_id = state.heroes[opposing_side].hero_id
            else:
                target_type = "card"
                target_id = random.choice(state.board[opposing_side])
            use_event = UseCardEvent(
                side=state.active,
                card_id=card_id,
                target_type=target_type,
                target_id=target_id)
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

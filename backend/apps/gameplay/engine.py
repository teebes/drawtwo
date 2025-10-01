"""
Gameplay engine to process events. Each function takes 1 event
and returns:
* the new state (without modifying the initial state)
* updates
* events
"""

import random
from typing import List


# Gameplay events
from apps.gameplay.schemas.events import (
    CardRetaliationEvent,
    ChooseAIMoveEvent,
    DealDamageEvent,
    DrawCardEvent,
    DrawPhaseEvent,
    EndTurnEvent,
    GameEvent,
    MainPhaseEvent,
    PlayCardEvent,
    RefreshPhaseEvent,
    StartGameEvent,
    UseCardEvent,
    UseHeroEvent,
)

# Gameplay updates
from apps.gameplay.schemas.updates import (
    CardDestroyedUpdate,
    DamageUpdate,
    DrawCardUpdate,
    DrawPhaseUpdate,
    EndTurnUpdate,
    GameOverUpdate,
    MainPhaseUpdate,
    PlayCardUpdate,
    RefreshPhaseUpdate,
)

# Gameplay errors
from apps.gameplay.schemas.errors import EnergyError

from .schemas import (
    CardDamageUpdate,
    GameState,
    GameUpdate,
    HeroDamageUpdate,
    ResolvedEvent,
    CardInPlay)

from apps.gameplay.traits import apply_traits

def resolve_event(state: GameState) -> ResolvedEvent:
    """
    Resolve an event and return the updated state, any new events to process,
    and any updates to send to the client.
    """

    event = state.event_queue.pop(0)

    print("\033[92m# %s #\033[0m" % event)

    events = []
    updates = []
    # The new state will be mutated by the handlers
    new_state: GameState = state.model_copy(deep=True)

    if isinstance(event, StartGameEvent):
        resolved_event = handle_start_game(new_state, event)

    elif isinstance(event, RefreshPhaseEvent):
        resolved_event = handle_refresh_phase(new_state, event)

    elif isinstance(event, DrawPhaseEvent):
        resolved_event = handle_draw_phase(new_state, event)

    elif isinstance(event, MainPhaseEvent):
        resolved_event = handle_main_phase(new_state, event)

    elif isinstance(event, EndTurnEvent):
        resolved_event = handle_end_turn(new_state, event)

    elif isinstance(event, DealDamageEvent):
        resolved_event = handle_deal_damage(new_state, event)

    elif isinstance(event, DrawCardEvent):
        resolved_event = handle_draw_card(new_state, event)

    elif isinstance(event, PlayCardEvent):
        resolved_event = handle_play_card(new_state, event)

    elif isinstance(event, UseCardEvent):
        resolved_event = handle_use_card(new_state, event)

    elif isinstance(event, UseHeroEvent):
        resolved_event = handle_use_hero(new_state, event)

    elif isinstance(event, CardRetaliationEvent):
        resolved_event = handle_card_retaliation(new_state, event)

    elif isinstance(event, ChooseAIMoveEvent):
        resolved_event = handle_choose_ai_move(new_state, event)

    else:
        raise ValueError(f"Invalid event: {event}")

    new_state.event_queue.extend(resolved_event.events)
    resolved_event.state = new_state
    return resolved_event


def handle_start_game(state: GameState, event:GameEvent) -> ResolvedEvent:
    state.phase = "start"

    hand_size = state.config.hand_start_size
    if hand_size < 0: hand_size = 0

    events = []

    for _ in range(hand_size):
        events.append(DrawCardEvent(side=state.active))

    events.append(RefreshPhaseEvent(side=state.active))

    return ResolvedEvent(
        state=state,
        events=events,
        updates=[],
        errors=[]
    )


def handle_refresh_phase(state: GameState, event: RefreshPhaseEvent) -> ResolvedEvent:
    state.phase = "refresh"
    state.mana_pool[event.side] = state.turn
    state.mana_used[event.side] = 0
    events = [DrawPhaseEvent(side=event.side)]
    updates = [RefreshPhaseUpdate(side=state.active)]
    return ResolvedEvent(
        state=state,
        events=events,
        updates=updates,
        errors=[]
    )


def handle_draw_phase(state: GameState, event: GameEvent) -> ResolvedEvent:
    state.phase = "draw"
    events = [DrawCardEvent(side=event.side), MainPhaseEvent(side=event.side)]
    updates = [DrawPhaseUpdate(side=event.side)]
    return ResolvedEvent(
        state=state,
        events=events,
        updates=updates,
        errors=[]
    )


def handle_main_phase(state: GameState, event: GameEvent) -> ResolvedEvent:
    state.phase = "main"

    events = []

    # If the new active side is an AI, queue up a choose ai move event
    #if event.side in state.ai_sides:
    #    events = [ChooseAIMoveEvent(side=event.side)]

    updates = [MainPhaseUpdate(side=event.side)]
    return ResolvedEvent(
        state=state,
        events=events,
        updates=updates,
        errors=[]
    )


def handle_end_turn(state: GameState, event: GameEvent) -> ResolvedEvent:

    # Mark all cards on the board as not exhausted
    for card_on_board in state.board[event.side]:
        state.cards[card_on_board].exhausted = False
    # Mark the hero as not exhausted
    state.heroes[event.side].exhausted = False

    end_of_turn_active = state.active

    state.active = "side_b" if state.active == "side_a" else "side_a"
    if state.active == "side_a":
        state.turn += 1
    state.phase = "start"
    events = [RefreshPhaseEvent(side=state.active)]
    updates = [EndTurnUpdate(side=end_of_turn_active)]
    return ResolvedEvent(
        state=state,
        events=events,
        updates=updates,
        errors=[]
    )


def handle_draw_card(state: GameState, event: GameEvent) -> ResolvedEvent:
    deck = state.decks[event.side]

    try:
        card_id = deck.pop(0)
    except IndexError:
        # No more cards in the deck
        opposing_side = "side_b" if event.side == "side_a" else "side_a"
        events = []
        updates = [GameOverUpdate(side=event.side, winner=opposing_side)]
        return ResolvedEvent(
            state=state,
            events=events,
            updates=updates,
            errors=[]
        )

    state.hands[event.side].append(card_id)

    events = []
    updates = [DrawCardUpdate(side=event.side, card_id=card_id)]
    return ResolvedEvent(
        state=state,
        events=events,
        updates=updates,
        errors=[]
    )


def handle_play_card(state: GameState, event: PlayCardEvent) -> ResolvedEvent:
    card = state.cards[event.card_id]

    # Make sure that the player has enough energy to play the card
    usable_mana = state.mana_pool[event.side] - state.mana_used[event.side]
    if card.cost > usable_mana:
        return ResolvedEvent(
            state=state,
            events=[],
            updates=[],
            errors=[EnergyError(message="Not enough energy to play the card")]
        )

    state.hands[event.side].remove(event.card_id)

    if card.card_type == "spell":
        state.graveyard[event.side].append(event.card_id)
    else:
        state.board[event.side].insert(event.position, event.card_id)

    state.mana_used[event.side] += state.cards[event.card_id].cost

    events = []
    updates = []

    play_card_update = PlayCardUpdate(
        side=event.side,
        card_id=event.card_id,
        position=event.position,
        target_type=event.target_type,
        target_id=event.target_id)

    updates.append(play_card_update)

    trait_events, trait_updates = apply_traits(state, play_card_update)

    events.extend(trait_events)
    updates.extend(trait_updates)

    return ResolvedEvent(
        state=state,
        events=events,
        updates=updates,
        errors=[]
    )


def handle_use_card(state: GameState, event: GameEvent) -> ResolvedEvent:
    deal_damage_event = DealDamageEvent(
        side=event.side,
        damage_type="physical",
        source_type="card",
        source_id=event.card_id,
        target_type=event.target_type,
        target_id=event.target_id,
        damage=state.cards[event.card_id].attack)
    return ResolvedEvent(
        state=state,
        events=[deal_damage_event],
        updates=[],
        errors=[]
    )


def handle_use_hero(state: GameState, event: UseHeroEvent) -> ResolvedEvent:
    from apps.gameplay.traits import handle_card_action
    hero = state.heroes[event.side]
    events = []
    updates = []

    for action in hero.hero_power.actions:
        print('action: %s' % action)
        _events, _updates = handle_card_action(state, hero, action, event)
        events.extend(_events)
        updates.extend(_updates)

    # deal_damage_event = DealDamageEvent(
    #     side=event.side,
    #     damage_type="physical",
    #     source_type="hero",
    #     source_id=event.hero_id,
    #     target_type=event.target_type,
    #     target_id=event.target_id,
    #     damage=state.heroes[event.side].attack)
    return ResolvedEvent(
        state=state,
        events=events,
        updates=updates,
        errors=[]
    )


def handle_deal_damage(state: GameState, event: DealDamageEvent) -> ResolvedEvent:
    events = []
    updates = []

    target_type = event.target_type
    opposing_side = "side_b" if event.side == "side_a" else "side_a"

    # Get the source
    if event.source_type == "hero":
        source = state.heroes[event.side]
    elif event.source_type == "card":
        source = state.cards[event.source_id]
    else:
        raise NotImplementedError

    # Get the target
    if event.target_type == "hero":
        target = state.heroes[opposing_side]
    elif event.target_type == "card":
        target = state.cards[event.target_id]
    else:
        raise NotImplementedError

    setattr(source, "exhausted", True)

    updates = [DamageUpdate(
        side=event.side,
        source_type=event.source_type,
        source_id=event.source_id,
        target_type=event.target_type,
        target_id=event.target_id,
        damage=event.damage
    )]

    if target_type == "hero":

        hero = target
        hero.health -= event.damage

        if hero.health <= 0:
            # If the hero dies, that is a game over event
            state.winner = event.side
            updates.append(GameOverUpdate(side=event.side, winner=event.side))

    if target_type == "card":
        # target is card
        target = state.cards[event.target_id]
        target.health -= event.damage
        if target.health <= 0:
            state.board[opposing_side].remove(event.target_id)

            # Deathrattle
            card_destroy_update = CardDestroyedUpdate(
                side=event.side,
                card_id=event.target_id
            )
            trait_events, trait_updates = apply_traits(state, card_destroy_update)
            events.extend(trait_events)
            updates.extend(trait_updates)
        else:
            # Determine if we need to retaliate
            should_retaliate = (
                event.retaliate
                and event.damage_type == "physical"
                and target_type == "card"
            )

            # Ranged trait doesn't get retaliated against
            if event.source_type == "card" and should_retaliate:
                has_ranged_trait = lambda trait: trait.type == "ranged"
                source_has_ranged_trait = any(
                    has_ranged_trait(trait)
                    for trait in state.cards[event.source_id].traits
                )
                if source_has_ranged_trait:
                    should_retaliate = False

            if should_retaliate:
                events.append(DealDamageEvent(
                    side=opposing_side,
                    damage_type="physical",
                    source_type="card",
                    source_id=event.target_id,
                    target_type=event.source_type,
                    target_id=event.source_id,
                    damage=target.attack,
                    retaliate=False
                ))

    return ResolvedEvent(
        state=state,
        events=events,
        updates=updates,
        errors=[]
    )


def handle_card_retaliation(state: GameState, event: GameEvent) -> ResolvedEvent:
    source_card_id = event.card_id
    source_card = state.cards[source_card_id]
    target_card_id = event.target_id
    target_card = state.cards[target_card_id]
    target_card.health -= source_card.attack
    if target_card.health <= 0:
        state.board[event.side].remove(target_card_id)
        return ResolvedEvent(
            state=state,
            events=[],
            updates=[CardDestroyedUpdate(side=event.side, card_id=target_card_id)],
            errors=[]
        )
    else:
        return ResolvedEvent(
            state=state,
            events=[],
            updates=[CardDamageUpdate(
                        side=event.side,
                        card_id=target_card_id,
                        damage=source_card.attack)])


def handle_choose_ai_move(state: GameState, event: ChooseAIMoveEvent) -> ResolvedEvent:
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
            return ResolvedEvent(
                state=state,
                events=[play_event, choose_ai_move],
                updates=[],
                errors=[]
            )

    # See if there's a card that can be used to attack, and if there is,
    # attack the hero.
    for card_id in state.board[state.active]:
        card = state.cards[card_id]

        if card.exhausted: continue

        if event.script.strategy == "rush":
            target_type = "hero"
            target_id = state.heroes[opposing_side].hero_id
        elif event.script.strategy == "control":
            target_type = "card"
            target_id = random.choice(state.board[opposing_side])
        else:
            # 50/50 chance to attack hero or card
            if random.random() < 0.5:
                target_type = "hero"
                target_id = state.heroes[opposing_side].hero_id
            else:
                target_type = "card"
                try:
                    target_id = random.choice(state.board[opposing_side])
                except IndexError:
                    target_type = "hero"
                    target_id = state.heroes[opposing_side].hero_id

        use_event = UseCardEvent(
            side=state.active,
            card_id=card_id,
            target_type=target_type,
            target_id=target_id)
        #choose_ai_move = ChooseAIMoveEvent(side=state.active)
        return ResolvedEvent(
            state=state,
            events=[use_event],
            updates=[],
            errors=[]
        )

    return ResolvedEvent(
        state=state,
        events=[EndTurnEvent(side=state.active)],
        updates=[],
        errors=[]
    )

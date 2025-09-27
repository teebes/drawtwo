from apps.gameplay.schemas import (
    GameState,
    GameEvent,
    GameUpdate,
    CardInPlay,
    Trait,
)

from apps.builder.schemas import (
    CardActionDraw,
    CardActionDamage,
    CardAction,
)

from apps.gameplay.schemas.events import (
    DrawCardEvent,
    DealDamageEvent,
)

from apps.gameplay.schemas.updates import (
    PlayCardUpdate,
    GameUpdate,
)



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

def handle_card_actions(state: GameState, card: CardInPlay, trait: Trait, update: GameUpdate) -> tuple[list[GameEvent], list[GameUpdate]]:
    events = []
    updates = []
    for card_action in trait.actions:
        _events, _updates = handle_card_action(state, card, card_action, update)
        events.extend(_events)
        updates.extend(_updates)
    return events, updates

def handle_card_action(state: GameState, card: CardInPlay, card_action: CardAction, update: GameUpdate) -> tuple[list[GameEvent], list[GameUpdate]]:
    events = []
    updates = []

    if isinstance(card_action, CardActionDraw):
        events.append(DrawCardEvent(side=state.active, amount=card_action.amount))

    elif isinstance(card_action, CardActionDamage):
        events.append(DealDamageEvent(
            side=state.active,
            damage_type="physical" if card.card_type == "minion" else "spell",
            card_id=card.card_id,
            target_type=update.target_type,
            target_id=update.target_id,
            source_type="card",
            source_id=update.card_id,
            damage=card_action.amount,
            retaliate=False
        ))

    return events, updates

# Individual trait handlers

def handle_charge_trait(state: GameState, update: PlayCardUpdate, card: CardInPlay, trait: Trait) -> tuple[list[GameEvent], list[GameUpdate]]:
    """Charge: Can attack immediately when played"""
    card.exhausted = False
    return [], []

def handle_battlecry_trait(state: GameState, update: PlayCardUpdate, card: CardInPlay, trait: Trait) -> tuple[list[GameEvent], list[GameUpdate]]:
    """Battlecry: Effect triggers when card is played"""
    return handle_card_actions(state, card, trait, update)

def handle_deathrattle_trait(state: GameState, update: PlayCardUpdate, card: CardInPlay, trait: Trait) -> tuple[list[GameEvent], list[GameUpdate]]:
    """Deathrattle: Effect triggers when card is destroyed"""
    return handle_card_actions(state, card, trait, update)

# Registry of trait handlers
TRAIT_HANDLERS = {
    "charge": handle_charge_trait,
    "battlecry": handle_battlecry_trait,
    "deathrattle": handle_deathrattle_trait,
}
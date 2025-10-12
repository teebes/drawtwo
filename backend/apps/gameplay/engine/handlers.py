"""
Effect handlers for the engine.
"""

from pydantic import TypeAdapter
from apps.builder.schemas import Action
from apps.gameplay.engine.actions import handle_action
from apps.gameplay.engine.dispatcher import register
from apps.gameplay.schemas.effects import (
    DamageEffect,
    EndTurnEffect,
    DrawEffect,
    MarkExhaustedEffect,
    NewPhaseEffect,
    PlayEffect,
    StartGameEffect,
    UseHeroEffect,
    UseCardEffect,
)
from apps.gameplay.schemas.events import (
    DamageEvent,
    DrawEvent,
    EndTurnEvent,
    GameOverEvent,
    NewPhaseEvent,
    PlayEvent,
)
from apps.gameplay.schemas.game import GameState
from apps.gameplay.schemas.engine import (
    Result,
    Success,
    Rejected,
)


@register("effect_draw")
def draw(effect: DrawEffect, state: GameState) -> Result:

    deck = state.decks[effect.side]
    try:
        card_id = deck.pop(0)
    except IndexError:
        opposing_side = "side_b" if effect.side == "side_a" else "side_a"
        go_event = GameOverEvent(side=effect.side, winner=opposing_side)
        return Success(new_state = state, events=[go_event])

    state.hands[effect.side].append(card_id)
    return Success(
        new_state=state,
        events=[DrawEvent(side=effect.side, card_id=card_id)]
    )

@register("effect_play")
def play(effect: PlayEffect, state: GameState) -> Result:

    card = state.cards[effect.source_id]

    # Make sure that the player has enough energy to play the card
    usable_mana = state.mana_pool[effect.side] - state.mana_used[effect.side]
    if card.cost > usable_mana:
        return Rejected(reason="Not enough energy to play the card")

    state.hands[effect.side].remove(effect.source_id)

    if card.card_type == "spell":
        state.graveyard[effect.side].append(effect.source_id)
    else:
        state.board[effect.side].insert(effect.position, effect.source_id)

    state.mana_used[effect.side] += card.cost

    return Success(
        new_state=state,
        events=[PlayEvent(
            side=effect.side,
            card_id=effect.source_id,
            position=effect.position,
            target_type=effect.target_type,
            target_id=effect.target_id,
        )]
    )

@register("effect_damage")
def damage(effect: DamageEffect, state: GameState) -> Result:
    events = []

    target_type = effect.target_type
    opposing_side = "side_b" if effect.side == "side_a" else "side_a"

    # Get the source
    if effect.source_type == "hero":
        source = state.heroes[effect.side]
    elif effect.source_type == "card":
        source = state.cards[effect.source_id]
    else:
        raise NotImplementedError

    # Get the target
    if effect.target_type == "hero":
        target = state.heroes[opposing_side]
    elif effect.target_type == "card":
        target = state.cards[effect.target_id]
    else:
        raise NotImplementedError

    setattr(source, "exhausted", True)

    events = [DamageEvent(
        side=effect.side,
        source_type=effect.source_type,
        source_id=effect.source_id,
        target_type=effect.target_type,
        target_id=effect.target_id,
        damage=effect.damage
    )]

    if target_type == "hero":

        hero = target
        hero.health -= effect.damage

        if hero.health <= 0:
            # If the hero dies, that is a game over event
            state.winner = effect.side
            events.append(GameOverEvent(side=effect.side, winner=effect.side))

    if target_type == "card":
        # target is card
        target = state.cards[effect.target_id]
        target.health -= effect.damage
        if target.health <= 0:
            state.board[opposing_side].remove(effect.target_id)
        else:
            # Determine if we need to retaliate
            should_retaliate = (
                effect.retaliate
                and effect.damage_type == "physical"
                and target_type == "card"
            )

            # Ranged trait doesn't get retaliated against
            if effect.source_type == "card" and should_retaliate:
                has_ranged_trait = lambda trait: trait.type == "ranged"
                source_has_ranged_trait = any(
                    has_ranged_trait(trait)
                    for trait in state.cards[effect.source_id].traits
                )
                if source_has_ranged_trait:
                    should_retaliate = False

            if should_retaliate:
                events.append(DamageEvent(
                    side=opposing_side,
                    damage_type="physical",
                    source_type="card",
                    source_id=effect.target_id,
                    target_type=effect.source_type,
                    target_id=effect.source_id,
                    damage=target.attack,
                    retaliate=False
                ))

    return Success(
        new_state=state,
        events=events,
    )

@register("effect_mark_exhausted")
def mark_exhausted(effect: MarkExhaustedEffect, state: GameState) -> Result:
    if effect.target_type == "card":
        state.cards[effect.target_id].exhausted = True
    elif effect.target_type == "hero":
        state.heroes[effect.side].exhausted = True
    return Success(new_state=state)

@register("effect_use_card")
def use_card(effect: UseCardEffect, state: GameState) -> Result:
    damage_effect = DamageEffect(
        side=effect.side,
        damage_type="physical",
        source_type="card",
        source_id=effect.card_id,
        target_type=effect.target_type,
        target_id=effect.target_id,
        damage=state.cards[effect.card_id].attack
    )
    mark_exhausted_effect = MarkExhaustedEffect(
        side=effect.side,
        target_type="card",
        target_id=effect.card_id
    )
    child_effects = [mark_exhausted_effect, damage_effect]
    return Success(new_state=state, child_effects=child_effects)

@register("effect_use_hero")
def use_hero(effect: UseHeroEffect, state: GameState) -> Result:
    hero = state.heroes[effect.side]

    if hero.exhausted:
        return Rejected(reason="Hero is exhausted")

    child_effects = []

    # Parse out hero power actions
    for action in hero.hero_power.actions:
        action = TypeAdapter(Action).validate_python(action)
        child_effects.extend(
            handle_action(state, effect, action))

    # Mark hero exhausted first
    mark_exhausted_effect = MarkExhaustedEffect(
        side=effect.side,
        target_type="hero",
        target_id=effect.source_id
    )
    child_effects.append(mark_exhausted_effect)

    return Success(new_state=state, child_effects=child_effects)

@register("effect_end_turn")
def end_turn(effect: EndTurnEffect, state: GameState) -> Result:
    # Mark all cards on the board as not exhausted
    for card_on_board in state.board[effect.side]:
        state.cards[card_on_board].exhausted = False

    # Mark the hero as not exhausted
    state.heroes[effect.side].exhausted = False

    # End of turn means the other side is up next
    new_active = "side_b" if state.active == "side_a" else "side_a"

    return Success(
        child_effects=[NewPhaseEffect(side=new_active, phase="start")],
        events=[EndTurnEvent(side=state.active)],
        new_state=state,
    )

@register("effect_phase")
def new_phase(effect: NewPhaseEffect, state: GameState) -> Result:
    child_effects = []

    if effect.phase == 'start':
        state.active = effect.side
        if state.active == "side_a":
            state.turn += 1
        refresh_phase = NewPhaseEffect(side=effect.side, phase='refresh')
        child_effects.append(refresh_phase)

    elif effect.phase == 'refresh':
        state.mana_pool[effect.side] = state.turn
        state.mana_used[effect.side] = 0
        draw_phase = NewPhaseEffect(side=effect.side, phase='draw')
        child_effects.append(draw_phase)

    elif effect.phase == 'draw':
        child_effects.extend([
            DrawEffect(side=effect.side),
            NewPhaseEffect(side=effect.side, phase='main'),
        ])

    state.phase = effect.phase

    return Success(
        new_state=state,
        child_effects=child_effects,
        events=[NewPhaseEvent(side=effect.side, phase=effect.phase)]
    )

@register("effect_start_game")
def start_game(effect: StartGameEffect, state: GameState) -> Result:
    hand_size = max(state.config.hand_start_size, 0)
    child_effects = []
    # Starting side draws cards
    child_effects.extend([
        DrawEffect(side=effect.side)
        for _ in range(hand_size)
    ])
    # Opposing side draws cards
    opposite_side = "side_b" if effect.side == "side_a" else "side_a"
    child_effects.extend([
        DrawEffect(side=opposite_side)
        for _ in range(hand_size)
    ])
    # Start phase
    child_effects.append(NewPhaseEffect(side=effect.side, phase='start'))
    print('%s child effects' % len(child_effects))
    return Success(new_state=state, child_effects=child_effects)

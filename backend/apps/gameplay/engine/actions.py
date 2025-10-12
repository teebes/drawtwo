from typing import List, Literal
from apps.builder.schemas import Action, DamageAction
from apps.gameplay.schemas.effects import Effect, DamageEffect, ActionSourceEffect
from apps.gameplay.schemas.game import GameState

def handle_action(
    state: GameState,
    effect: ActionSourceEffect,
    action: Action,
) -> List[Effect]:
    effects = []

    # This can be called by 3 things:
    # * playing a card with a battlecry
    # * using a hero power
    # * dealing damage with a spell
    if isinstance(action, DamageAction):
        # Figure out who the target of the action should be
        if action.target == "hero":
            target_type = "hero"
            target_id = state.heroes[state.opposite_side].hero_id
        elif action.target == "creature":
            target_type = "card"
            target_id = effect.target_id or state.board[state.opposite_side][0]
        else:
            target_type = effect.target_type
            target_id = effect.target_id

        effects.append(DamageEffect(
            side=state.active,
            damage_type="physical",
            source_type=effect.source_type,
            source_id=effect.source_id,
            target_type=target_type,
            target_id=target_id,
            damage=action.amount
        ))

    return effects
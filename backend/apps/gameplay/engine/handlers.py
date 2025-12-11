"""
Effect handlers for the engine.
"""

from pydantic import TypeAdapter
from apps.builder.schemas import Action
from apps.gameplay.engine.dispatcher import register
from apps.gameplay.schemas.effects import (
    AttackEffect,
    DamageEffect,
    EndTurnEffect,
    DrawEffect,
    HealEffect,
    MarkExhaustedEffect,
    NewPhaseEffect,
    PlayEffect,
    RemoveEffect,
    StartGameEffect,
    SummonEffect,
    TempManaBoostEffect,
    UseHeroEffect,
)
from apps.gameplay.schemas.events import (
    CreatureDeathEvent,
    DamageEvent,
    DrawEvent,
    EndTurnEvent,
    GameOverEvent,
    HealEvent,
    NewPhaseEvent,
    PlayEvent,
    RemoveEvent,
    SummonEvent,
    TempManaBoostEvent,
    UseHeroEvent,
)
from apps.gameplay.schemas.game import GameState, CardInPlay, Creature
from apps.gameplay.schemas.engine import (
    Result,
    Success,
    Rejected,
)

def spawn_creature(card: CardInPlay, state: GameState, side, position: int=0) -> Creature:
    # Creature being spawned
    creature_id = str(int(state.last_creature_id) + 1)
    state.last_creature_id = int(creature_id)
    creature = Creature(
        creature_id=creature_id,
        card_id=card.card_id,
        name=card.name,
        description=card.description,
        attack=card.attack,
        attack_max=card.attack,
        health=card.health,
        health_max=card.health,
        traits=card.traits,
        exhausted=True,
        art_url=card.art_url,
    )
    state.creatures[creature_id] = creature
    state.board[side].insert(position, creature_id)
    return creature


@register("effect_draw")
def draw(effect: DrawEffect, state: GameState) -> Result:

    deck = state.decks[effect.side]
    events = []

    for _ in range(effect.amount):
        try:
            card_id = deck.pop(0)
        except IndexError:
            opposing_side = "side_b" if effect.side == "side_a" else "side_a"
            go_event = GameOverEvent(side=effect.side, winner=opposing_side)
            return Success(new_state = state, events=[go_event])

        state.hands[effect.side].append(card_id)
        events.append(
            DrawEvent(
                side=effect.side,
                card_id=card_id,
                target_type="card",
                target_id=card_id,
            ))

    return Success(
        new_state=state,
        events=events
    )

def has_stealth(creature: Creature) -> bool:
    """Check if a creature has the stealth trait."""
    return any(trait.type == "stealth" for trait in creature.traits)


@register("effect_play")
def play(effect: PlayEffect, state: GameState) -> Result:

    card = state.cards[effect.source_id]

    # Make sure that the player has enough energy to play the card
    usable_mana = state.mana_pool[effect.side] - state.mana_used[effect.side]
    if card.cost > usable_mana:
        return Rejected(reason="Not enough energy to play the card")

    # STEALTH VALIDATION: Cannot directly target stealthed creatures with spells
    if effect.target_type == "creature" and effect.target_id:
        target_creature = state.creatures.get(effect.target_id)
        if target_creature and has_stealth(target_creature):
            # Only reject if it's an ENEMY creature
            opposing_side = "side_b" if effect.side == "side_a" else "side_a"
            if effect.target_id in state.board[opposing_side]:
                return Rejected(reason="Cannot target stealthed creatures")

    state.hands[effect.side].remove(effect.source_id)

    creature_id = None
    if card.card_type == "spell":
        state.graveyard[effect.side].append(effect.source_id)
    else:
        # The old way was to add the same card object that was in hand to the board
        #state.board[effect.side].insert(effect.position, effect.source_id)
        # Now we create a new creature object and add it to the board
        creature = spawn_creature(
            card=card,
            state=state,
            side=effect.side,
            position=effect.position,
        )
        creature_id = creature.creature_id

    state.mana_used[effect.side] += card.cost

    return Success(
        new_state=state,
        events=[PlayEvent(
            side=effect.side,
            source_type="card",
            source_id=effect.source_id,
            position=effect.position,
            target_type=effect.target_type,
            target_id=effect.target_id,
            creature_id=creature_id,
        )]
    )

@register("effect_damage")
def damage(effect: DamageEffect, state: GameState) -> Result:
    child_effects = []
    events = []

    target_type = effect.target_type
    opposing_side = "side_b" if effect.side == "side_a" else "side_a"

    # Get the source
    if effect.source_type == "hero":
        source = state.heroes[effect.side]
    elif effect.source_type == "card":
        source = state.cards[effect.source_id]
    elif effect.source_type == "creature":
        source = state.creatures[effect.source_id]
    else:
        raise NotImplementedError

    # Get the target
    if effect.target_type == "hero":
        target = state.heroes[opposing_side]
    elif effect.target_type == "card":
        target = state.cards[effect.target_id]
    elif effect.target_type == "creature":
        target = state.creatures[effect.target_id]
    else:
        raise NotImplementedError

    events = [DamageEvent(
        side=effect.side,
        source_type=effect.source_type,
        source_id=effect.source_id,
        target_type=effect.target_type,
        target_id=effect.target_id,
        damage=effect.damage,
        is_retaliation=effect.is_retaliation,
    )]

    if target_type == "hero":

        hero = target
        hero.health -= effect.damage

        if hero.health <= 0:
            # If the hero dies, that is a game over event
            state.winner = effect.side
            events.append(GameOverEvent(side=effect.side, winner=effect.side))

    if target_type == "card" or target_type == "creature":
        # Target is a creature on the board (we already fetched it above)
        target.health -= effect.damage

        # Creature death
        if target.health <= 0:
            state.board[opposing_side].remove(effect.target_id)

            events.append(CreatureDeathEvent(
                side=opposing_side,
                source_type=effect.source_type,
                source_id=effect.source_id,
                creature=target,
                target_type=effect.target_type,
                target_id=effect.target_id,
            ))

        if target.health > 0 or state.config.death_retaliation:
            # Determine if we need to retaliate
            should_retaliate = (
                effect.retaliate
                and effect.damage_type == "physical"
                and (target_type == "card" or target_type == "creature")
                and effect.source_type != "card"
            )

            # Ranged trait doesn't get retaliated against
            if ((effect.source_type == "card" or effect.source_type == "creature")
            and should_retaliate):
                has_ranged_trait = lambda trait: trait.type == "ranged"
                # Source is already fetched above
                source_has_ranged_trait = any(
                    has_ranged_trait(trait)
                    for trait in source.traits
                )
                if source_has_ranged_trait:
                    should_retaliate = False

            if should_retaliate:
                child_effects.append(DamageEffect(
                    side=opposing_side,
                    damage_type="physical",
                    source_type="creature",
                    source_id=effect.target_id,
                    target_type=effect.source_type,
                    target_id=effect.source_id,
                    damage=target.attack,
                    retaliate=False,
                    is_retaliation=True
                ))

    return Success(
        new_state=state,
        events=events,
        child_effects=child_effects,
    )

@register("effect_heal")
def heal(effect: HealEffect, state: GameState) -> Result:
    """
    Heal effect handler - restores health to a target.
    """
    events = []

    # Determine which side to look for target (heal targets friendlies on same side)
    target_side = effect.side

    # Get the source
    if effect.source_type == "hero":
        source = state.heroes[effect.side]
    elif effect.source_type == "card":
        source = state.cards[effect.source_id]
    elif effect.source_type == "creature":
        source = state.creatures[effect.source_id]
    else:
        raise NotImplementedError(f"Unknown source type: {effect.source_type}")

    # Get the target
    if effect.target_type == "hero":
        target = state.heroes[target_side]
    elif effect.target_type == "card":
        target = state.cards[effect.target_id]
    elif effect.target_type == "creature":
        target = state.creatures[effect.target_id]
    else:
        raise NotImplementedError(f"Unknown target type: {effect.target_type}")

    # Apply healing
    target.health += effect.amount

    if target.health > target.health_max:
        target.health = target.health_max

    events = [HealEvent(
        side=effect.side,
        source_type=effect.source_type,
        source_id=effect.source_id,
        target_type=effect.target_type,
        target_id=effect.target_id,
        amount=effect.amount
    )]

    return Success(
        new_state=state,
        events=events,
    )

@register("effect_mark_exhausted")
def mark_exhausted(effect: MarkExhaustedEffect, state: GameState) -> Result:
    if effect.target_type == "card":
        state.cards[effect.target_id].exhausted = True
    elif effect.target_type == "creature":
        state.creatures[effect.target_id].exhausted = True
    elif effect.target_type == "hero":
        state.heroes[effect.side].exhausted = True
    return Success(new_state=state)

def has_taunt(creature: Creature) -> bool:
    """Check if a creature has the taunt trait."""
    return any(trait.type == "taunt" for trait in creature.traits)


def get_taunt_creatures(state: GameState, side: str) -> list[str]:
    """Get all creature IDs with taunt on the given side."""
    taunt_creatures = []
    for creature_id in state.board[side]:
        creature = state.creatures.get(creature_id)
        if creature and has_taunt(creature):
            taunt_creatures.append(creature_id)
    return taunt_creatures


@register("effect_attack")
def attack(effect: AttackEffect, state: GameState) -> Result:
    # effect.card_id is actually a creature_id (on the board)
    creature = state.creatures.get(effect.card_id)
    if not creature:
        return Rejected(reason=f"Creature {effect.card_id} does not exist")

    # Validate that the creature belongs to the attacking side
    if effect.card_id not in state.board[effect.side]:
        return Rejected(reason=f"You do not control creature {effect.card_id}")

    # Validate that the target belongs to the opponent
    opposing_side = state.opposite_side
    if effect.target_type == "creature":
        if effect.target_id not in state.board[opposing_side]:
            return Rejected(reason=f"Target creature is not on opponent's board")
    elif effect.target_type == "hero":
        opposing_hero = state.heroes.get(opposing_side)
        if not opposing_hero or opposing_hero.hero_id != effect.target_id:
            return Rejected(reason=f"Target is not the opponent's hero")

    # Check if creature is exhausted
    if creature.exhausted:
        return Rejected(reason="Creature is exhausted")

    # STEALTH VALIDATION: Cannot directly target stealthed creatures
    if effect.target_type == "creature":
        target_creature = state.creatures.get(effect.target_id)
        if target_creature and has_stealth(target_creature):
            return Rejected(reason="Cannot target stealthed creatures")

    # TAUNT VALIDATION: If opponent has creatures with taunt, must attack one of them
    taunt_creatures = get_taunt_creatures(state, opposing_side)
    if taunt_creatures:
        # If there are taunt creatures, the target must be one of them
        if effect.target_type == "hero":
            return Rejected(reason="Cannot attack hero while enemy has creatures with Taunt")
        elif effect.target_type == "creature":
            if effect.target_id not in taunt_creatures:
                return Rejected(reason="Must attack a creature with Taunt")

    # STEALTH REMOVAL: Remove stealth trait when attacking
    creature.traits = [trait for trait in creature.traits if trait.type != "stealth"]

    damage_effect = DamageEffect(
        side=effect.side,
        damage_type="physical",
        source_type="creature",
        source_id=effect.card_id,
        target_type=effect.target_type,
        target_id=effect.target_id,
        damage=creature.attack
    )
    mark_exhausted_effect = MarkExhaustedEffect(
        side=effect.side,
        target_type="creature",
        target_id=effect.card_id
    )
    child_effects = [mark_exhausted_effect, damage_effect]
    return Success(new_state=state, child_effects=child_effects)


@register("effect_use_hero")
def use_hero(effect: UseHeroEffect, state: GameState) -> Result:
    # Lazy import to avoid circular dependency
    from apps.gameplay.services import GameService
    from apps.builder.schemas import HealAction

    hero = state.heroes.get(effect.side)
    if not hero:
        return Rejected(reason=f"Hero not found for side {effect.side}")

    # Validate that the source_id matches the hero for this side
    if hero.hero_id != effect.source_id:
        return Rejected(reason=f"You do not control hero {effect.source_id}")

    # Determine if this hero power targets friendlies or enemies
    targets_friendly = any(
        isinstance(action, HealAction) and action.target == 'friendly'
        for action in hero.hero_power.actions
    )

    # Validate that the target belongs to the correct side (if there is a target)
    if effect.target_type:
        if targets_friendly:
            # For healing/friendly powers, target must be on own side
            if effect.target_type == "creature":
                if effect.target_id not in state.board[effect.side]:
                    return Rejected(reason=f"Target creature is not on your board")
            elif effect.target_type == "hero":
                own_hero = state.heroes.get(effect.side)
                if not own_hero or own_hero.hero_id != effect.target_id:
                    return Rejected(reason=f"Target is not your hero")
        else:
            # For damage/enemy powers, target must be on opponent's side
            opposing_side = state.opposite_side
            if effect.target_type == "creature":
                if effect.target_id not in state.board[opposing_side]:
                    return Rejected(reason=f"Target creature is not on opponent's board")
                # STEALTH VALIDATION: Cannot directly target stealthed creatures with hero powers
                target_creature = state.creatures.get(effect.target_id)
                if target_creature and has_stealth(target_creature):
                    return Rejected(reason="Cannot target stealthed creatures")
            elif effect.target_type == "hero":
                opposing_hero = state.heroes.get(opposing_side)
                if not opposing_hero or opposing_hero.hero_id != effect.target_id:
                    return Rejected(reason=f"Target is not the opponent's hero")

    if hero.exhausted:
        return Rejected(reason="Hero is exhausted")

    child_effects = []

    use_hero_event = UseHeroEvent(
        side=effect.side,
        source_type="hero",
        source_id=effect.source_id,
        target_type=effect.target_type,
        target_id=effect.target_id,
    )

    # Parse out hero power actions
    for action in hero.hero_power.actions:
        action = TypeAdapter(Action).validate_python(action)
        child_effects.extend(
            GameService.compile_action(
                state=state,
                event=use_hero_event,
                action=action,
            )
        )

    # Mark hero exhausted first
    mark_exhausted_effect = MarkExhaustedEffect(
        side=effect.side,
        target_type="hero",
        target_id=effect.source_id,
    )
    child_effects.append(mark_exhausted_effect)

    return Success(
        new_state=state,
        child_effects=child_effects,
        events=[use_hero_event]
    )

@register("effect_end_turn")
def end_turn(effect: EndTurnEffect, state: GameState) -> Result:
    # Mark all creatures on the board as not exhausted
    for creature_id in state.board[effect.side]:
        state.creatures[creature_id].exhausted = False

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
        state.mana_pool[effect.side] = min(state.turn, 10)
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
    return Success(new_state=state, child_effects=child_effects)


@register("effect_remove")
def remove(effect: RemoveEffect, state: GameState) -> Result:
    """
    Remove effect handler - removes a creature from the board without triggering deathrattle.

    This is different from damage-based removal which triggers CreatureDeathEvent.
    Remove is used for effects like "silence and destroy" or "return to hand" style mechanics.
    """
    events = []

    # Determine which side the target is on (opposite of the effect side)
    opposing_side = "side_b" if effect.side == "side_a" else "side_a"

    # Validate that the target exists and is on the board
    if effect.target_id not in state.board[opposing_side]:
        return Rejected(reason=f"Target creature {effect.target_id} is not on the board")

    # Get the target creature
    target_creature = state.creatures.get(effect.target_id)
    if not target_creature:
        return Rejected(reason=f"Target creature {effect.target_id} does not exist")

    # Remove the creature from the board
    state.board[opposing_side].remove(effect.target_id)

    # Remove from creatures dict
    del state.creatures[effect.target_id]

    # Emit RemoveEvent (does NOT trigger deathrattle)
    events.append(RemoveEvent(
        side=effect.side,
        source_type=effect.source_type,
        source_id=effect.source_id,
        target_type=effect.target_type,
        target_id=effect.target_id,
    ))

    return Success(
        new_state=state,
        events=events,
        child_effects=[]
    )

@register("effect_temp_mana_boost")
def temp_mana_boost(effect: TempManaBoostEffect, state: GameState) -> Result:
    state.mana_pool[effect.side] += effect.amount
    return Success(
        new_state=state,
        events=[
            TempManaBoostEvent(side=effect.side, amount=effect.amount)
        ])

@register("effect_summon")
def summon(effect: SummonEffect, state: GameState) -> Result:
    card_slug = effect.target

    # Look up the card template from state
    if card_slug not in state.summonable_cards:
        return Rejected(reason=f"Card '{card_slug}' not found in summonable cards")

    template = state.summonable_cards[card_slug]

    # Summon only works for creatures
    if template.card_type != 'creature':
        return Rejected(reason=f"Cannot summon non-creature card '{card_slug}'")

    # Create a new card instance with a unique card_id
    card_id = max((int(cid) for cid in state.cards.keys()), default=0) + 1
    card = CardInPlay(
        card_type=template.card_type,
        card_id=str(card_id),
        template_slug=template.template_slug,
        name=template.name,
        description=template.description,
        attack=template.attack,
        health=template.health,
        cost=template.cost,
        traits=template.traits,
        exhausted=True,
        art_url=template.art_url,
    )

    # Add the card to the game state
    state.cards[str(card_id)] = card

    # Spawn the creature on the board at position 0 (leftmost)
    # Summons always go to the side of the source card
    spawn_creature(card, state, effect.side, position=0)

    return Success(
        new_state=state,
        events=[SummonEvent(
            side=effect.side,
            source_type="card",
            source_id=effect.source_id,
            target_type="card",
            target_id=card.card_id,
        )]
    )
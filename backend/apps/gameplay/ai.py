import random

from apps.builder.schemas import DeckScript, DamageAction, HealAction, RemoveAction, BuffAction
from apps.gameplay.schemas.game import GameState
from apps.gameplay.schemas.effects import Effect, UseHeroEffect, PlayEffect, AttackEffect
from apps.gameplay.engine.handlers import get_taunt_creatures


class AIMoveChooser:
    """Handles AI move selection logic for game AI players."""

    @staticmethod
    def choose_move(state: GameState, script: DeckScript) -> Effect | None:
        """
        Choose the next move for an AI player.

        Priority order:
        1. Hero power (if available and not exhausted)
        2. Spell cards (if affordable)
        3. Creature cards (if affordable)
        4. Creature attacks
        """
        mana_pool = state.mana_pool[state.active]
        mana_used = state.mana_used[state.active]
        mana_available = mana_pool - mana_used

        opposing_side = "side_b" if state.active == "side_a" else "side_a"

        # 1. Check if hero power can be used
        active_hero = state.heroes.get(state.active)
        if active_hero and not active_hero.exhausted:
            if AIMoveChooser._hero_power_requires_target(active_hero.hero_power):
                targets = AIMoveChooser._get_hero_power_targets(active_hero.hero_power, state, state.active)
                if targets:
                    target_type, target_id = random.choice(targets)
                    return UseHeroEffect(
                        side=state.active,
                        source_id=active_hero.hero_id,
                        target_type=target_type,
                        target_id=target_id,
                    )
            else:
                # Hero power doesn't need a target, use it
                return UseHeroEffect(
                    side=state.active,
                    source_id=active_hero.hero_id,
                )

        # 2. Check for spell cards that can be played
        for card_id in state.hands[state.active]:
            card = state.cards[card_id]
            if card.cost <= mana_available and card.card_type == 'spell':
                if AIMoveChooser._spell_requires_target(card):
                    targets = AIMoveChooser._get_spell_targets(card, state, state.active)
                    if targets:
                        target_type, target_id = random.choice(targets)
                        # Convert 'creature' to 'card' for backend compatibility
                        backend_target_type = "card" if target_type == "creature" else target_type
                        return PlayEffect(
                            side=state.active,
                            source_id=card_id,
                            position=0,
                            target_type=backend_target_type,
                            target_id=target_id,
                        )
                else:
                    # Spell doesn't need a target, play it
                    return PlayEffect(
                        side=state.active,
                        source_id=card_id,
                        position=0,
                    )

        # 3. See if there's a creature card that can be played from hand to board
        for card_id in state.hands[state.active]:
            card = state.cards[card_id]
            if card.cost <= mana_available and card.card_type == 'creature':
                card_id_to_play = card_id
                return PlayEffect(
                    side=state.active,
                    source_id=card_id_to_play,
                    position=0,
                )

        # 4. Check for taunt creatures on the opposing board
        taunt_creatures = get_taunt_creatures(state, opposing_side)

        # 5. See if there's a creature that can be used to attack
        for creature_id in state.board[state.active]:
            creature = state.creatures[creature_id]

            if creature.exhausted:
                continue

            # If there are taunt creatures, we MUST attack one of them
            if taunt_creatures:
                target_type = "creature"
                target_id = random.choice(taunt_creatures)
            elif script.strategy == "rush":
                target_type = "hero"
                target_id = state.heroes[opposing_side].hero_id
            elif script.strategy == "control":
                target_type = "creature"
                target_id = random.choice(state.board[opposing_side])
            else:
                # 50/50 chance to attack hero or card
                if random.random() < 0.5:
                    target_type = "hero"
                    target_id = state.heroes[opposing_side].hero_id
                else:
                    target_type = "creature"
                    try:
                        target_id = random.choice(state.board[opposing_side])
                    except IndexError:
                        target_type = "hero"
                        target_id = state.heroes[opposing_side].hero_id

            return AttackEffect(
                side=state.active,
                card_id=creature_id,
                target_type=target_type,
                target_id=target_id)

        return None

    @staticmethod
    def _spell_requires_target(card) -> bool:
        """Check if a spell card requires a target based on its traits."""
        for trait in card.traits:
            for action in trait.actions:
                # Single target actions require a target
                if isinstance(action, (DamageAction, HealAction, RemoveAction, BuffAction)):
                    if getattr(action, "scope", "single") != 'all':
                        # Damage/heal that always goes to a fixed hero doesn't require a target
                        if isinstance(action, DamageAction) and action.target == "hero":
                            continue
                        if isinstance(action, HealAction) and action.target == "hero":
                            continue
                        if isinstance(action, BuffAction) and action.target == "hero":
                            continue
                        return True
        return False

    @staticmethod
    def _get_spell_targets(card, state: GameState, active_side: str) -> list[tuple[str, str]]:
        """
        Get valid targets for a spell card.
        Returns: list of (target_type, target_id) tuples
        """
        opposing_side = "side_b" if active_side == "side_a" else "side_a"
        targets = []

        # Determine target scope - check if any action targets friendlies
        targets_friendly = False
        for trait in card.traits:
            for action in trait.actions:
                if isinstance(action, HealAction) and action.target in ('friendly', 'creature', 'hero'):
                    targets_friendly = True
                    break
                if isinstance(action, BuffAction):
                    targets_friendly = True
                    break
            if targets_friendly:
                break

        # Collect targets based on scope
        for trait in card.traits:
            for action in trait.actions:
                if targets_friendly:
                    if isinstance(action, HealAction):
                        if action.target in ['hero', 'friendly']:
                            # Own hero
                            own_hero = state.heroes.get(active_side)
                            if own_hero:
                                targets.append(("hero", own_hero.hero_id))
                        if action.target in ['creature', 'friendly']:
                            # Own creatures
                            for creature_id in state.board[active_side]:
                                targets.append(("creature", creature_id))
                    if isinstance(action, BuffAction):
                        if action.target in ['hero', 'friendly']:
                            own_hero = state.heroes.get(active_side)
                            if own_hero:
                                targets.append(("hero", own_hero.hero_id))
                        if action.target in ['creature', 'friendly']:
                            # Buff targets own creatures
                            for creature_id in state.board[active_side]:
                                targets.append(("creature", creature_id))
                else:
                    if isinstance(action, (DamageAction, RemoveAction)):
                        if action.target in ['hero', 'enemy']:
                            # Opposing hero
                            opposing_hero = state.heroes.get(opposing_side)
                            if opposing_hero:
                                targets.append(("hero", opposing_hero.hero_id))
                        if action.target in ['creature', 'enemy']:
                            # Opposing creatures (excluding stealthed)
                            for creature_id in state.board[opposing_side]:
                                creature = state.creatures.get(creature_id)
                                if creature:
                                    has_stealth = any(creature_trait.type == "stealth" for creature_trait in creature.traits)
                                    if not has_stealth:
                                        targets.append(("creature", creature_id))

        # Remove duplicates
        targets = list(set(targets))
        return targets

    @staticmethod
    def _hero_power_requires_target(hero_power) -> bool:
        """Check if a hero power requires a target."""
        for action in hero_power.actions:
            if isinstance(action, (DamageAction, HealAction, RemoveAction)):
                if action.scope == 'single' and action.target in ['hero', 'creature', 'enemy', 'friendly']:
                    return True
            if isinstance(action, BuffAction):
                if action.scope == 'single' and action.target in ['creature', 'friendly']:
                    return True
        return False

    @staticmethod
    def _get_hero_power_targets(hero_power, state: GameState, active_side: str) -> list[tuple[str, str]]:
        """
        Get valid targets for a hero power.
        Returns: list of (target_type, target_id) tuples
        """
        opposing_side = "side_b" if active_side == "side_a" else "side_a"
        targets = []

        # Determine target scope - check if any action is a HealAction with friendly target
        targets_friendly = any(
            (isinstance(action, HealAction) and action.target == 'friendly')
            or isinstance(action, BuffAction)
            for action in hero_power.actions
        )

        # Collect targets based on scope
        for action in hero_power.actions:
            if targets_friendly:
                if isinstance(action, HealAction):
                    if action.target in ['hero', 'friendly']:
                        # Own hero
                        own_hero = state.heroes.get(active_side)
                        if own_hero:
                            targets.append(("hero", own_hero.hero_id))
                    if action.target in ['creature', 'friendly']:
                        # Own creatures
                        for creature_id in state.board[active_side]:
                            targets.append(("creature", creature_id))
                if isinstance(action, BuffAction):
                    if action.target in ['hero', 'friendly']:
                        # Own hero
                        own_hero = state.heroes.get(active_side)
                        if own_hero:
                            targets.append(("hero", own_hero.hero_id))
                    if action.target in ['creature', 'friendly']:
                        # Own creatures
                        for creature_id in state.board[active_side]:
                            targets.append(("creature", creature_id))
            else:
                if isinstance(action, (DamageAction, RemoveAction)):
                    if action.target in ['hero', 'enemy']:
                        # Opposing hero
                        opposing_hero = state.heroes.get(opposing_side)
                        if opposing_hero:
                            targets.append(("hero", opposing_hero.hero_id))
                    if action.target in ['creature', 'enemy']:
                        # Opposing creatures (excluding stealthed)
                        for creature_id in state.board[opposing_side]:
                            creature = state.creatures.get(creature_id)
                            if creature:
                                has_stealth = any(creature_trait.type == "stealth" for creature_trait in creature.traits)
                                if not has_stealth:
                                    targets.append(("creature", creature_id))

        # Remove duplicates
        targets = list(set(targets))
        return targets

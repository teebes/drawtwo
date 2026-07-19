from itertools import combinations
from typing import Iterable, Literal

from pydantic import TypeAdapter, ValidationError

from apps.builder.schemas import (
    Action,
    BuffAction,
    DamageAction,
    HealAction,
    RemoveAction,
    SilenceAction,
)
from apps.gameplay.engine.handlers import get_taunt_creatures
from apps.gameplay.schemas.commands import (
    AttackCommand,
    Command,
    ConcedeCommand,
    EndTurnCommand,
    MulliganCommand,
    PlayCardCommand,
    UseHeroCommand,
)
from apps.gameplay.schemas.game import CardInPlay, GameState, HeroInPlay

TargetType = Literal["creature", "hero"]
Target = tuple[TargetType, str]


def _opposing_side(side: str) -> str:
    return "side_b" if side == "side_a" else "side_a"


def _dedupe_commands(commands: Iterable[Command]) -> list[Command]:
    seen = set()
    result = []
    for command in commands:
        key = command.model_dump_json()
        if key in seen:
            continue
        seen.add(key)
        result.append(command)
    return result


def _dedupe_targets(targets: Iterable[Target]) -> list[Target]:
    return list(dict.fromkeys(targets))


def _actions_from_card(card: CardInPlay) -> list[Action]:
    actions: list[Action] = []
    for trait in card.traits or []:
        for raw_action in getattr(trait, "actions", None) or []:
            try:
                actions.append(TypeAdapter(Action).validate_python(raw_action))
            except ValidationError:
                continue
    return actions


def _actions_from_hero(hero: HeroInPlay) -> list[Action]:
    actions: list[Action] = []
    for raw_action in hero.hero_power.actions or []:
        try:
            actions.append(TypeAdapter(Action).validate_python(raw_action))
        except ValidationError:
            continue
    return actions


def _has_stealth(state: GameState, creature_id: str) -> bool:
    creature = state.creatures.get(creature_id)
    if not creature:
        return False
    return any(trait.type == "stealth" for trait in creature.traits)


def _enemy_creature_targets(state: GameState, side: str) -> list[Target]:
    opposing_side = _opposing_side(side)
    return [
        ("creature", creature_id)
        for creature_id in state.board.get(opposing_side, [])
        if not _has_stealth(state, creature_id)
    ]


def _friendly_creature_targets(state: GameState, side: str) -> list[Target]:
    return [("creature", creature_id) for creature_id in state.board.get(side, [])]


def _enemy_hero_target(state: GameState, side: str) -> list[Target]:
    hero = state.heroes.get(_opposing_side(side))
    return [("hero", hero.hero_id)] if hero else []


def _friendly_hero_target(state: GameState, side: str) -> list[Target]:
    hero = state.heroes.get(side)
    return [("hero", hero.hero_id)] if hero else []


def _action_requires_selected_target(action: Action) -> bool:
    if getattr(action, "scope", "single") == "all":
        return False
    if isinstance(action, DamageAction) and action.target in ("hero", "self"):
        return False
    if isinstance(action, HealAction) and action.target == "hero":
        return False
    if isinstance(action, BuffAction) and action.target == "hero":
        return False
    return isinstance(
        action,
        (DamageAction, HealAction, RemoveAction, SilenceAction, BuffAction),
    )


def _targets_for_action(action: Action, state: GameState, side: str) -> list[Target]:
    if not _action_requires_selected_target(action):
        return []

    if isinstance(action, DamageAction):
        if action.target == "enemy":
            hero_targets = _enemy_hero_target(state, side)
            # Taunt blocks selecting the enemy hero for physical damage;
            # spell damage bypasses it
            if action.damage_type == "physical" and get_taunt_creatures(
                state, _opposing_side(side)
            ):
                hero_targets = []
            return _enemy_creature_targets(state, side) + hero_targets
        if action.target == "friendly":
            return _friendly_creature_targets(state, side) + _friendly_hero_target(
                state, side
            )
        if action.target == "creature":
            return _enemy_creature_targets(state, side)

    if isinstance(action, RemoveAction):
        return _enemy_creature_targets(state, side)

    if isinstance(action, SilenceAction):
        return _enemy_creature_targets(state, side)

    if isinstance(action, HealAction):
        if action.target == "friendly":
            return _friendly_creature_targets(state, side) + _friendly_hero_target(
                state, side
            )
        if action.target == "creature":
            return _friendly_creature_targets(state, side)

    if isinstance(action, BuffAction):
        if action.target == "friendly":
            return _friendly_creature_targets(state, side) + _friendly_hero_target(
                state, side
            )
        if action.target == "creature":
            return _friendly_creature_targets(state, side)

    return []


def _targets_for_actions(
    actions: list[Action],
    state: GameState,
    side: str,
) -> list[Target]:
    targets: list[Target] = []
    for action in actions:
        targets.extend(_targets_for_action(action, state, side))
    return _dedupe_targets(targets)


def _requires_selected_target(actions: list[Action]) -> bool:
    return any(_action_requires_selected_target(action) for action in actions)


def _play_positions(state: GameState, side: str, card: CardInPlay) -> list[int]:
    if card.card_type == "spell":
        return [0]
    return list(range(len(state.board.get(side, [])) + 1))


def _mulligan_commands(state: GameState, side: str) -> list[Command]:
    if state.mulligan_done.get(side, False):
        return []

    options = [
        card_id
        for card_id in state.mulligan_options.get(side, [])
        if card_id in state.hands.get(side, [])
    ]

    commands: list[Command] = []
    for count in range(len(options) + 1):
        for card_ids in combinations(options, count):
            commands.append(MulliganCommand(card_ids=list(card_ids)))
    return commands


def _play_card_commands(state: GameState, side: str) -> list[Command]:
    mana_available = state.mana_pool.get(side, 0) - state.mana_used.get(side, 0)
    commands: list[Command] = []

    for card_id in state.hands.get(side, []):
        card = state.cards.get(card_id)
        if not card or card.cost > mana_available:
            continue

        actions = _actions_from_card(card)
        requires_target = _requires_selected_target(actions)
        targets = _targets_for_actions(actions, state, side) if requires_target else []
        if requires_target and not targets:
            continue

        for position in _play_positions(state, side, card):
            if not requires_target:
                commands.append(PlayCardCommand(card_id=card_id, position=position))
                continue

            for target_type, target_id in targets:
                commands.append(
                    PlayCardCommand(
                        card_id=card_id,
                        position=position,
                        target_type=target_type,
                        target_id=target_id,
                    )
                )

    return commands


def _attack_commands(state: GameState, side: str) -> list[Command]:
    opposing_side = _opposing_side(side)
    taunt_creatures = get_taunt_creatures(state, opposing_side)
    commands: list[Command] = []

    if taunt_creatures:
        targets = [("creature", creature_id) for creature_id in taunt_creatures]
    else:
        targets = _enemy_creature_targets(state, side) + _enemy_hero_target(state, side)

    for creature_id in state.board.get(side, []):
        creature = state.creatures.get(creature_id)
        if not creature or creature.exhausted or creature.attack <= 0:
            continue
        for target_type, target_id in targets:
            commands.append(
                AttackCommand(
                    card_id=creature_id,
                    target_type=target_type,
                    target_id=target_id,
                )
            )

    return commands


def _hero_commands(state: GameState, side: str) -> list[Command]:
    hero = state.heroes.get(side)
    if not hero or hero.exhausted:
        return []

    mana_available = state.mana_pool.get(side, 0) - state.mana_used.get(side, 0)
    if (hero.hero_power.cost or 0) > mana_available:
        return []

    actions = _actions_from_hero(hero)
    requires_target = _requires_selected_target(actions)

    if not requires_target:
        return [UseHeroCommand(hero_id=hero.hero_id)]

    targets = _targets_for_actions(actions, state, side)
    commands: list[Command] = []
    for target_type, target_id in targets:
        commands.append(
            UseHeroCommand(
                hero_id=hero.hero_id,
                target_type=target_type,
                target_id=target_id,
            )
        )
    return commands


def list_legal_commands(
    state: GameState,
    side: str,
    *,
    include_concede: bool = False,
) -> list[Command]:
    """
    Enumerate human-facing commands an agent can submit from this position.

    This intentionally returns commands, not lower-level effects, so bots and
    training jobs use the same behavioral surface as human clients.
    """
    if state.winner != "none":
        return []

    commands: list[Command] = []

    if state.phase == "mulligan":
        commands.extend(_mulligan_commands(state, side))
    elif state.phase == "main" and state.active == side:
        commands.extend(_play_card_commands(state, side))
        commands.extend(_attack_commands(state, side))
        commands.extend(_hero_commands(state, side))
        commands.append(EndTurnCommand())

    if include_concede:
        commands.append(ConcedeCommand())

    return _dedupe_commands(commands)

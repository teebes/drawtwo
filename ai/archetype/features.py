from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ai.data.replays import to_command_dict

FEATURE_VERSION = "archetype_linear_v1"


def _bucket(value: Any, edges: tuple[int, ...]) -> str:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        number = 0

    for edge in edges:
        if number <= edge:
            return f"le_{edge}"
    return f"gt_{edges[-1]}"


def _add(features: Counter[str], name: str, value: float = 1.0) -> None:
    if value:
        features[name] += value


def _public_state(observation: Mapping[str, Any] | None) -> dict[str, Any]:
    if not observation:
        return {}
    if "public_state" in observation:
        public_state = observation.get("public_state") or {}
        return dict(public_state)
    return dict(observation)


def _opposing_side(side: str) -> str:
    return "side_b" if side == "side_a" else "side_a"


def _side_map(state: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = state.get(key) or {}
    return dict(value) if isinstance(value, Mapping) else {}


def _card(state: Mapping[str, Any], card_id: str | None) -> dict[str, Any]:
    if not card_id:
        return {}
    cards = _side_map(state, "cards")
    card = cards.get(str(card_id)) or {}
    return dict(card) if isinstance(card, Mapping) else {}


def _creature(state: Mapping[str, Any], creature_id: str | None) -> dict[str, Any]:
    if not creature_id:
        return {}
    creatures = _side_map(state, "creatures")
    creature = creatures.get(str(creature_id)) or {}
    return dict(creature) if isinstance(creature, Mapping) else {}


def _hero_for_side(state: Mapping[str, Any], side: str) -> dict[str, Any]:
    hero = _side_map(state, "heroes").get(side) or {}
    return dict(hero) if isinstance(hero, Mapping) else {}


def _side_for_creature(state: Mapping[str, Any], creature_id: str | None) -> str | None:
    if not creature_id:
        return None
    board = _side_map(state, "board")
    for side, creature_ids in board.items():
        if str(creature_id) in (creature_ids or []):
            return side
    return None


def _side_for_hero_id(state: Mapping[str, Any], hero_id: str | None) -> str | None:
    if not hero_id:
        return None
    for side, hero in _side_map(state, "heroes").items():
        if isinstance(hero, Mapping) and hero.get("hero_id") == hero_id:
            return side
    return None


def _trait_types(entity: Mapping[str, Any]) -> list[str]:
    result = []
    for trait in entity.get("traits") or []:
        if isinstance(trait, Mapping) and trait.get("type"):
            result.append(str(trait["type"]))
    return sorted(result)


def _target_features(
    features: Counter[str],
    state: Mapping[str, Any],
    actor_side: str,
    command: Mapping[str, Any],
) -> None:
    target_type = command.get("target_type")
    target_id = command.get("target_id")
    if not target_type or not target_id:
        _add(features, "cmd:target=none")
        return

    if target_type == "card":
        target_type = "creature"
    _add(features, f"cmd:target_type={target_type}")

    if target_type == "hero":
        target_side = _side_for_hero_id(state, str(target_id))
        if target_side:
            relation = "enemy" if target_side != actor_side else "friendly"
            _add(features, f"cmd:target_relation={relation}")
            target_hero = _hero_for_side(state, target_side)
            _add(
                features,
                f"cmd:target_hero_health={_bucket(target_hero.get('health'), (5, 10, 15, 20, 30))}",
            )
        return

    target_side = _side_for_creature(state, str(target_id))
    target_creature = _creature(state, str(target_id))
    if target_side:
        relation = "enemy" if target_side != actor_side else "friendly"
        _add(features, f"cmd:target_relation={relation}")
    if target_creature:
        _add(
            features,
            f"cmd:target_attack={_bucket(target_creature.get('attack'), (0, 1, 2, 4, 7))}",
        )
        _add(
            features,
            f"cmd:target_health={_bucket(target_creature.get('health'), (1, 2, 4, 7))}",
        )
        for trait_type in _trait_types(target_creature):
            _add(features, f"cmd:target_trait={trait_type}")


def _add_context_features(
    features: Counter[str],
    state: Mapping[str, Any],
    actor_side: str,
    row: Mapping[str, Any] | None,
    legal_commands: list[Any] | None,
) -> list[str]:
    opponent_side = _opposing_side(actor_side)
    phase = state.get("phase") or (row or {}).get("phase") or "unknown"
    turn = state.get("turn") or (row or {}).get("turn") or 0
    own_hero = _hero_for_side(state, actor_side)
    opponent_hero = _hero_for_side(state, opponent_side)
    board = _side_map(state, "board")
    hands = _side_map(state, "hands")
    hand_counts = _side_map(state, "hand_counts")
    decks = _side_map(state, "decks")
    deck_counts = _side_map(state, "deck_counts")
    mana_pool = _side_map(state, "mana_pool")
    mana_used = _side_map(state, "mana_used")

    context_keys: list[str] = []

    def add_context(name: str, value: float = 1.0) -> None:
        _add(features, name, value)
        if len(context_keys) < 16:
            context_keys.append(name)

    add_context("bias")
    add_context(f"ctx:side={actor_side}")
    add_context(f"ctx:phase={phase}")
    add_context(f"ctx:turn={_bucket(turn, (0, 1, 2, 4, 7, 10, 15))}")

    if legal_commands is not None:
        add_context(
            f"ctx:legal_count={_bucket(len(legal_commands), (1, 2, 4, 8, 16, 32))}"
        )

    if own_hero:
        add_context(f"ctx:own_hero={own_hero.get('template_slug', 'unknown')}")
        add_context(
            f"ctx:own_health={_bucket(own_hero.get('health'), (5, 10, 15, 20, 30))}"
        )
    if opponent_hero:
        add_context(
            f"ctx:opponent_hero={opponent_hero.get('template_slug', 'unknown')}"
        )
        add_context(
            f"ctx:opponent_health={_bucket(opponent_hero.get('health'), (5, 10, 15, 20, 30))}"
        )

    own_board = list(board.get(actor_side) or [])
    opponent_board = list(board.get(opponent_side) or [])
    own_hand = list(hands.get(actor_side) or [])
    own_deck = list(decks.get(actor_side) or [])
    opponent_hand_count = hand_counts.get(
        opponent_side, len(hands.get(opponent_side) or [])
    )
    opponent_deck_count = deck_counts.get(
        opponent_side, len(decks.get(opponent_side) or [])
    )

    add_context(f"ctx:own_board={_bucket(len(own_board), (0, 1, 2, 3, 5, 7))}")
    add_context(
        f"ctx:opponent_board={_bucket(len(opponent_board), (0, 1, 2, 3, 5, 7))}"
    )
    add_context(f"ctx:own_hand={_bucket(len(own_hand), (0, 1, 2, 4, 7, 10))}")
    add_context(
        f"ctx:opponent_hand={_bucket(opponent_hand_count, (0, 1, 2, 4, 7, 10))}"
    )
    add_context(f"ctx:own_deck={_bucket(len(own_deck), (0, 5, 10, 20, 30))}")
    add_context(f"ctx:opponent_deck={_bucket(opponent_deck_count, (0, 5, 10, 20, 30))}")

    mana_available = int(mana_pool.get(actor_side, 0) or 0) - int(
        mana_used.get(actor_side, 0) or 0
    )
    add_context(f"ctx:mana_available={_bucket(mana_available, (0, 1, 2, 4, 7, 10))}")

    own_total_attack = 0
    opponent_total_attack = 0
    for creature_id in own_board:
        own_total_attack += int(_creature(state, creature_id).get("attack", 0) or 0)
    for creature_id in opponent_board:
        opponent_total_attack += int(
            _creature(state, creature_id).get("attack", 0) or 0
        )
    add_context(
        f"ctx:own_board_attack={_bucket(own_total_attack, (0, 1, 3, 6, 10, 15))}"
    )
    add_context(
        f"ctx:opponent_board_attack={_bucket(opponent_total_attack, (0, 1, 3, 6, 10, 15))}"
    )

    for card_id in own_hand[:10]:
        card = _card(state, str(card_id))
        if card.get("template_slug"):
            _add(features, f"ctx:own_hand_card={card['template_slug']}")
            _add(features, f"ctx:own_hand_card_type={card.get('card_type', 'unknown')}")

    return context_keys


def command_features(
    observation: Mapping[str, Any] | None,
    actor_side: str,
    command: Any,
    *,
    row: Mapping[str, Any] | None = None,
    legal_commands: list[Any] | None = None,
) -> dict[str, float]:
    state = _public_state(observation)
    command_dict = to_command_dict(command)
    command_type = command_dict.get("type", "unknown")
    features: Counter[str] = Counter()
    context_keys = _add_context_features(
        features,
        state,
        actor_side,
        row,
        legal_commands,
    )

    command_keys: list[str] = []

    def add_command(name: str, value: float = 1.0) -> None:
        _add(features, name, value)
        if len(command_keys) < 16:
            command_keys.append(name)

    add_command(f"cmd:type={command_type}")

    if command_type == "cmd_play_card":
        card = _card(state, str(command_dict.get("card_id", "")))
        card_type = card.get("card_type", "unknown")
        add_command(f"cmd:play_card_type={card_type}")
        if card.get("template_slug"):
            add_command(f"cmd:play_template={card['template_slug']}")
        add_command(f"cmd:play_cost={_bucket(card.get('cost'), (0, 1, 2, 4, 7, 10))}")
        if card_type == "creature":
            add_command(
                f"cmd:play_attack={_bucket(card.get('attack'), (0, 1, 2, 4, 7))}"
            )
            add_command(f"cmd:play_health={_bucket(card.get('health'), (1, 2, 4, 7))}")
        for trait_type in _trait_types(card):
            add_command(f"cmd:play_trait={trait_type}")
        add_command(
            f"cmd:position={_bucket(command_dict.get('position'), (0, 1, 2, 4, 7))}"
        )
        _target_features(features, state, actor_side, command_dict)

    elif command_type == "cmd_attack":
        attacker = _creature(state, str(command_dict.get("card_id", "")))
        add_command(
            f"cmd:attacker_attack={_bucket(attacker.get('attack'), (0, 1, 2, 4, 7))}"
        )
        add_command(
            f"cmd:attacker_health={_bucket(attacker.get('health'), (1, 2, 4, 7))}"
        )
        _target_features(features, state, actor_side, command_dict)
        if command_dict.get("target_type") == "hero":
            add_command("cmd:attack_face")

    elif command_type == "cmd_use_hero":
        own_hero = _hero_for_side(state, actor_side)
        if own_hero.get("template_slug"):
            add_command(f"cmd:hero_power_template={own_hero['template_slug']}")
        _target_features(features, state, actor_side, command_dict)

    elif command_type == "cmd_mulligan":
        card_ids = list(command_dict.get("card_ids") or [])
        add_command(f"cmd:mulligan_count={_bucket(len(card_ids), (0, 1, 2, 3, 5))}")
        for card_id in card_ids[:10]:
            card = _card(state, str(card_id))
            if card.get("template_slug"):
                add_command(f"cmd:mulligan_template={card['template_slug']}")
                add_command(
                    f"cmd:mulligan_cost={_bucket(card.get('cost'), (0, 1, 2, 4, 7, 10))}"
                )

    elif command_type == "cmd_end_turn":
        add_command("cmd:pass")

    elif command_type == "cmd_concede":
        add_command("cmd:concede")

    for context_key in context_keys:
        for command_key in command_keys:
            _add(features, f"pair:{context_key}|{command_key}")

    return dict(features)

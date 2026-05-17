from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.gameplay.schemas.game import GameState


class AgentObservation(BaseModel):
    side: Literal["side_a", "side_b"]
    public_state: dict[str, Any]
    legal_context: dict[str, Any] = Field(default_factory=dict)


def _hidden_placeholders(prefix: str, count: int) -> list[str]:
    return [f"{prefix}_{index}" for index in range(count)]


def _card_ids_from_zone(zone: Any) -> set[str]:
    if not isinstance(zone, list):
        return set()
    return {str(card_id) for card_id in zone}


def _redact_hidden_card_records(filtered: dict[str, Any], side: str) -> None:
    visible_card_ids: set[str] = set()

    hands = filtered.get("hands") or {}
    visible_card_ids.update(_card_ids_from_zone(hands.get(side)))

    mulligan_options = filtered.get("mulligan_options") or {}
    visible_card_ids.update(_card_ids_from_zone(mulligan_options.get(side)))

    graveyard = filtered.get("graveyard") or {}
    for graveyard_side in ("side_a", "side_b"):
        visible_card_ids.update(_card_ids_from_zone(graveyard.get(graveyard_side)))

    creatures = filtered.get("creatures") or {}
    if isinstance(creatures, dict):
        for creature in creatures.values():
            if isinstance(creature, dict) and creature.get("card_id"):
                visible_card_ids.add(str(creature["card_id"]))

    cards = filtered.get("cards") or {}
    if isinstance(cards, dict):
        filtered["cards"] = {
            card_id: card
            for card_id, card in cards.items()
            if str(card_id) in visible_card_ids
        }


def filter_state_for_player(
    state: GameState | dict,
    side: str,
    *,
    redact_hidden_card_records: bool = False,
) -> dict[str, Any]:
    """
    Return a client/agent-safe state view for one side.

    The shape intentionally stays close to the existing frontend `GameState` so
    this can replace the previous WebSocket filter transparently. Hidden zones
    keep placeholder entries so existing UI count logic still works.
    """
    if hasattr(state, "model_dump"):
        filtered = state.model_dump(mode="json")
    else:
        filtered = dict(state)

    opposing_side = "side_b" if side == "side_a" else "side_a"

    hands = dict(filtered.get("hands") or {})
    hand_counts = {
        "side_a": len(hands.get("side_a", [])),
        "side_b": len(hands.get("side_b", [])),
    }
    hands[opposing_side] = _hidden_placeholders(
        f"hidden_hand_{opposing_side}", hand_counts[opposing_side]
    )
    filtered["hands"] = hands
    filtered["hand_counts"] = hand_counts

    decks = dict(filtered.get("decks") or {})
    deck_counts = {
        "side_a": len(decks.get("side_a", [])),
        "side_b": len(decks.get("side_b", [])),
    }
    for deck_side in ("side_a", "side_b"):
        decks[deck_side] = _hidden_placeholders(
            f"hidden_deck_{deck_side}", deck_counts[deck_side]
        )
    filtered["decks"] = decks
    filtered["deck_counts"] = deck_counts

    mulligan_options = dict(filtered.get("mulligan_options") or {})
    mulligan_options[opposing_side] = []
    filtered["mulligan_options"] = mulligan_options

    if redact_hidden_card_records:
        _redact_hidden_card_records(filtered, side)

    return filtered


def make_observation(state: GameState, side: str) -> AgentObservation:
    return AgentObservation(
        side=side,
        public_state=filter_state_for_player(
            state,
            side,
            redact_hidden_card_records=True,
        ),
    )

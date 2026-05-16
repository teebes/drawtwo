from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.gameplay.schemas.game import GameState


class AgentObservation(BaseModel):
    side: Literal["side_a", "side_b"]
    public_state: dict[str, Any]
    legal_context: dict[str, Any] = Field(default_factory=dict)


def _hidden_placeholders(prefix: str, count: int) -> list[str]:
    return [f"{prefix}_{index}" for index in range(count)]


def filter_state_for_player(state: GameState | dict, side: str) -> dict[str, Any]:
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

    return filtered


def make_observation(state: GameState, side: str) -> AgentObservation:
    return AgentObservation(
        side=side,
        public_state=filter_state_for_player(state, side),
    )

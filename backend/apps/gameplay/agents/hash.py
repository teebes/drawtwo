import hashlib
import json
from typing import Any

from apps.gameplay.schemas.game import GameState


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def state_hash(state: GameState) -> str:
    """
    Stable hash for replay verification and training datasets.
    """
    return hashlib.sha256(
        canonical_json(state.model_dump(mode="json")).encode("utf-8")
    ).hexdigest()

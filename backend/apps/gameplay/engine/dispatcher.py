import logging
from typing import Callable, Dict

from apps.gameplay.schemas.effects import Effect
from apps.gameplay.schemas.game import GameState
from apps.gameplay.schemas.engine import Result, Fault

logger = logging.getLogger(__name__)

# Handler signature
Handler = Callable[[Effect, GameState], Result]

_REGISTRY: Dict[str, Handler] = {}

def register(kind: str):
    """Decorator: register a handler for an effect kind."""
    def deco(fn: Handler) -> Handler:
        _REGISTRY[kind] = fn
        return fn
    return deco

def resolve(effect: Effect, state: GameState) -> Result:
    """Pure-ish resolver: deep-copy first (your choice), dispatch by kind."""
    st = state.model_copy(deep=True)
    handler = _REGISTRY.get(effect.type)
    logger.debug(f"\033[38;5;208m{effect}\033[0m")
    if not handler:
        return Fault(error_id="unknown_effect", reason="Unknown Effect")
    return handler(effect, st)

# Import handlers to register them (must be after register() is defined)
from apps.gameplay.engine import handlers  # noqa: E402, F401

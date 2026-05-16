from typing import Any

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from apps.gameplay.agents.hash import state_hash
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.schemas.commands import Command
from apps.gameplay.schemas.effects import Effect
from apps.gameplay.schemas.engine import Fault, Prevented, Rejected, Success
from apps.gameplay.schemas.events import GameOverEvent, NewPhaseEvent
from apps.gameplay.schemas.game import GameState


class SimulationError(BaseModel):
    type: str
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)


class SimulationResult(BaseModel):
    state: GameState
    events: list[Any] = Field(default_factory=list)
    updates: list[Any] = Field(default_factory=list)
    errors: list[SimulationError] = Field(default_factory=list)
    terminal: bool = False
    winner: str = "none"
    pre_state_hash: str
    post_state_hash: str


def _event_to_json(event):
    return event.model_dump(mode="json") if hasattr(event, "model_dump") else event


def _error_from_outcome(outcome) -> SimulationError:
    return SimulationError(
        type=outcome.type,
        reason=getattr(outcome, "reason", "Unknown outcome"),
        details=getattr(outcome, "details", {}) or {},
    )


def apply_effects(
    state: GameState,
    effects: list[Effect],
    *,
    max_effects: int = 1000,
) -> SimulationResult:
    """
    Resolve effects against a copy of state without touching the database.

    This mirrors the live engine's queue processing closely enough for search,
    self-play, and replay verification while avoiding Celery/WebSocket side
    effects.
    """
    from apps.gameplay import traits
    from apps.gameplay.services import GameService

    working_state = state.model_copy(deep=True)
    pre_hash = state_hash(working_state)
    queue = list(effects)
    all_events = []
    all_errors: list[SimulationError] = []
    processed = 0

    while queue and processed < max_effects:
        raw_effect = queue.pop(0)
        try:
            effect = TypeAdapter(Effect).validate_python(raw_effect)
        except ValidationError as exc:
            all_errors.append(
                SimulationError(
                    type="effect_validation_error",
                    reason="Invalid effect",
                    details={"errors": exc.errors()},
                )
            )
            continue

        result = resolve(effect, working_state)
        processed += 1

        if isinstance(result, Success):
            working_state = result.new_state

            if result.child_effects:
                queue = list(result.child_effects) + queue

            all_events.extend(result.events)

            for event in result.events:
                if isinstance(event, GameOverEvent):
                    working_state.winner = event.winner
                    queue = []
                    break

                trait_result = traits.apply(working_state, event)
                if isinstance(trait_result, Success):
                    working_state = trait_result.new_state
                if getattr(trait_result, "child_effects", None):
                    queue = list(trait_result.child_effects) + queue

                if isinstance(event, NewPhaseEvent):
                    # Live games also update timers here. The simulator leaves
                    # wall-clock timers out because self-play should not depend
                    # on real time.
                    pass

        elif isinstance(result, (Prevented, Rejected)):
            all_events.extend(result.events)
            all_errors.append(_error_from_outcome(result))

        elif isinstance(result, Fault):
            all_errors.append(
                SimulationError(
                    type=result.type,
                    reason=result.reason,
                    details={
                        **(result.details or {}),
                        "error_id": result.error_id,
                        "retryable": result.retryable,
                    },
                )
            )
            if not result.retryable:
                break

    if queue and processed >= max_effects:
        all_errors.append(
            SimulationError(
                type="simulation_effect_cap",
                reason="Simulation stopped after max_effects",
                details={"max_effects": max_effects},
            )
        )

    updates = GameService._events_to_updates(all_events)
    post_hash = state_hash(working_state)
    return SimulationResult(
        state=working_state,
        events=[_event_to_json(event) for event in all_events],
        updates=[
            update.model_dump(mode="json") if hasattr(update, "model_dump") else update
            for update in updates
        ],
        errors=all_errors,
        terminal=working_state.winner != "none",
        winner=working_state.winner,
        pre_state_hash=pre_hash,
        post_state_hash=post_hash,
    )


def apply_command(
    state: GameState,
    side: str,
    command: Command | dict,
    *,
    max_effects: int = 1000,
) -> SimulationResult:
    """
    Compile and resolve a human-facing command against a copy of state.
    """
    from apps.gameplay.services import GameService

    working_state = state.model_copy(deep=True)
    pre_hash = state_hash(working_state)

    try:
        command_dict = (
            command.model_dump(mode="json")
            if hasattr(command, "model_dump")
            else command
        )
        effects = GameService.compile_cmd(working_state, command_dict, side)
    except Exception as exc:
        return SimulationResult(
            state=working_state,
            errors=[
                SimulationError(
                    type="command_validation_error",
                    reason=str(exc),
                )
            ],
            pre_state_hash=pre_hash,
            post_state_hash=pre_hash,
        )

    return apply_effects(working_state, effects, max_effects=max_effects)

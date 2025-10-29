from typing import Literal, List, Dict, Union, Annotated, Literal, Optional
from pydantic import BaseModel, Field, Discriminator
import uuid

from apps.gameplay.schemas.effects import Effect
from apps.gameplay.schemas.events import Event
from apps.gameplay.schemas.game import GameState

class ResultBase(BaseModel):
    """
    A result is what is returned by an effect when it is resolved.
    """
    type: Literal['outcome'] = 'outcome'


class Success(ResultBase):
    """
    * The effect resolved normally, state mutated, and domain Events emitted.
    * Child effects may be enqueued (depth-first).
    * System behavior: process events, generate updates, continue queue.
    """
    type: Literal['outcome_success'] = 'outcome_success'
    new_state: GameState
    events: List[Event] = Field(default_factory=list)
    child_effects: List[Effect] = Field(default_factory=list)


class Prevented(ResultBase):
    """
    * The effect was canceled or replaced before resolution.
    * Domain concept: e.g. “Immune to damage” cancels a DealDamage effect.
    * Industry analogues: “replacement effects” in MTG, “interceptors” in some engines.
    * System behavior:
        * No state change.
        * Emit evt_effect_prevented (domain event). May be one or more events.
        * No updates except maybe a UI hint (“Immune”).
        * Continue queue.
    """
    type: Literal['outcome_prevented'] = 'outcome_prevented'
    reason: str
    details: dict = Field(default_factory=dict)
    events: List[Event] = Field(default_factory=list)


class Rejected(ResultBase):
    """
    * The effect violated domain rules (at enqueue OR resolution time).
    * Domain concept: not enough mana, exhausted, invalid target, target died, etc.
    * Industry analogue: "Fizzles" in MTG, "illegal action" in RTS.
    * System behavior:
        * No state change.
        * Emit evt_effect_rejected(reason=…). May be one or more events.
        * Send user-visible feedback: "Not enough energy", "Target is exhausted", etc.
        * Continue queue.
    """
    type: Literal['outcome_rejected'] = 'outcome_rejected'
    reason: str
    details: dict = Field(default_factory=dict)
    events: List[Event] = Field(default_factory=list)


class Fault(ResultBase):
    """
    * The engine itself failed (bug, unhandled exception, data corruption, timeout).
    * NOT for validation failures - use Rejected for those.
    * Not a domain outcome; this is an ops/system concern.
    * Industry analogue: "system fault," "task error," "dead letter."
    * System behavior:
        * Do not emit domain events (don't pollute game history).
        * Emit sys_effect_fault (system event) for observability/logging.
        * Apply retry/backoff if retryable=True.
        * If unrecoverable → dead-letter → abort game session or resync.
        * May emit a generic upd_error_actor ("Something went wrong") but not to opponent/spectators.
    """
    type: Literal['outcome_fault'] = 'outcome_fault'
    error_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reason: str
    retryable: bool = False
    details: dict = Field(default_factory=dict)


Result = Annotated[
    Union[Success, Prevented, Rejected, Fault],
    Discriminator('type')
]
from typing import Literal, List, Dict, Union, Annotated, Literal, Optional
from pydantic import BaseModel, Field, Discriminator

from apps.builder.schemas import TitleConfig, Trait

PHASE_ORDER = ['start', 'refresh', 'draw', 'main',]

Phase = Literal['start', 'refresh', 'draw', 'main', 'combat', 'end']


# ==== Actions ====

class ActionBase(BaseModel):
    type: str


class PlayCardAction(ActionBase):
    type: Literal["play_card_action"] = "play_card_action"
    card_id: str
    position: int
    target_type: Optional[Literal["card", "hero"]] = None
    target_id: Optional[str] = None


class UseCardAction(ActionBase):
    type: Literal["use_card_action"] = "use_card_action"
    card_id: str
    target_type: Literal["card", "hero"] = "card"
    target_id: str


class EndTurnAction(ActionBase):
    type: Literal["end_turn_action"] = "end_turn_action"


GameAction = Annotated[
    Union[PlayCardAction, UseCardAction, EndTurnAction],
    Discriminator('type')]

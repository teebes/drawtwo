from typing import Literal, List, Dict, Union, Annotated, Literal, Optional
from pydantic import BaseModel, Field, Discriminator

from apps.builder.schemas import TitleConfig, Trait

PHASE_ORDER = ['start', 'refresh', 'draw', 'main',]

Phase = Literal['start', 'refresh', 'draw', 'main', 'combat', 'end']


# ==== Actions ====

class ActionBase(BaseModel):
    type: str


class PlayCardAction(ActionBase):
    type: Literal["action_play_card"] = "action_play_card"
    card_id: str
    position: int
    target_type: Optional[Literal["card", "hero"]] = None
    target_id: Optional[str] = None


class UseCardAction(ActionBase):
    type: Literal["action_use_card"] = "action_use_card"
    card_id: str
    target_type: Literal["card", "hero"] = "card"
    target_id: str


class UseHeroAction(ActionBase):
    type: Literal["action_use_hero"] = "action_use_hero"
    hero_id: str
    target_type: Literal["card", "hero"] = "card"
    target_id: str


class EndTurnAction(ActionBase):
    type: Literal["action_end_turn"] = "action_end_turn"


GameAction = Annotated[
    Union[
        EndTurnAction,
        PlayCardAction,
        UseCardAction,
        UseHeroAction,
    ],
    Discriminator('type')]

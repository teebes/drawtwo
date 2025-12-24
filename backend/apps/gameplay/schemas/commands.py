from typing import Literal, List, Dict, Union, Annotated, Literal, Optional
from pydantic import BaseModel, Field, Discriminator

from apps.builder.schemas import TitleConfig, Trait

PHASE_ORDER = ['start', 'refresh', 'draw', 'main',]

Phase = Literal['start', 'refresh', 'draw', 'main', 'combat', 'end']


# ==== Actions ====

class CommandBase(BaseModel):
    type: str


class PlayCardCommand(CommandBase):
    type: Literal["cmd_play_card"] = "cmd_play_card"
    card_id: str
    position: int
    target_type: Optional[Literal["card", "creature", "hero"]] = None
    target_id: Optional[str] = None


class AttackCommand(CommandBase):
    type: Literal["cmd_attack"] = "cmd_attack"
    card_id: str
    target_type: Literal["card", "creature", "hero"] = "card"
    target_id: str


class UseHeroCommand(CommandBase):
    type: Literal["cmd_use_hero"] = "cmd_use_hero"
    hero_id: str
    target_type: Literal["card", "hero", "creature"] = "card"
    target_id: str


class EndTurnCommand(CommandBase):
    type: Literal["cmd_end_turn"] = "cmd_end_turn"


class ConcedeCommand(CommandBase):
    type: Literal["cmd_concede"] = "cmd_concede"


Command = Annotated[
    Union[
        AttackCommand,
        ConcedeCommand,
        EndTurnCommand,
        PlayCardCommand,
        UseHeroCommand,
    ],
    Discriminator('type')]

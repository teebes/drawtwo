from typing import Literal, List, Dict
from pydantic import BaseModel, Field


Phase = Literal['start', 'refresh', 'draw', 'main', 'combat', 'end']


class Event(BaseModel):
    type: str
    player: Literal['side_a', 'side_b']


class CardInPlay(BaseModel):
    template_id: str
    atk: int
    hp: int


class GameState(BaseModel):
    turn: int = 1
    active: Literal["side_a", "side_b"] = "side_a"
    phase: Phase = "start"
    event_queue: List[Event] = Field(
        default_factory=lambda: [Event(type="start_turn", player="side_a")]
    )
    board: Dict[str, List[CardInPlay]] = Field(
        default_factory=lambda: {
            "side_a": [],
            "side_b": [],
        }
    )
    hands: Dict[str, List[int]] = Field(
        default_factory=lambda: {
            "side_a": [],
            "side_b": [],
        }
    )
    deck: Dict[str, List[int]] = Field(
        default_factory=lambda: {
            "side_a": [],
            "side_b": [],
        }
    )
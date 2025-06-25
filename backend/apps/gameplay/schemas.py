from typing import Literal, List, Dict
from pydantic import BaseModel, Field


Phase = Literal['start', 'refresh', 'draw', 'main', 'combat', 'end']


class Event(BaseModel):
    type: str
    player: Literal['side_a', 'side_b']


class CardInPlay(BaseModel):
    card_id: int # Interal card ID for that game
    template_id: str # ID of the card template
    attack: int
    health: int
    cost: int
    traits: List[str]


class GameState(BaseModel):
    turn: int = 1
    active: Literal["side_a", "side_b"] = "side_a"
    phase: Phase = "start"
    event_queue: List[Event] = Field(
        default_factory=lambda: [Event(type="start_turn", player="side_a")]
    )
    # Centralized storage of all cards in the game by their unique ID
    cards: Dict[int, CardInPlay] = Field(default_factory=dict)

    # All zones now consistently store lists of card IDs that reference the cards dict
    board: Dict[str, List[int]] = Field(
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
    decks: Dict[str, List[int]] = Field(
        default_factory=lambda: {
            "side_a": [],
            "side_b": [],
        }
    )
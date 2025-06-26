from typing import Literal, List, Dict
from pydantic import BaseModel, Field


Phase = Literal['start', 'refresh', 'draw', 'main', 'combat', 'end']


class Event(BaseModel):
    type: str
    player: Literal['side_a', 'side_b']


class Trait(BaseModel):
    slug: str
    name: str
    data: dict = {}


class CardInPlay(BaseModel):
    card_id: int # Interal card ID for that game
    template_slug: str # ID of the card template
    attack: int
    health: int
    cost: int
    traits: List[Trait]


class HeroInPlay(BaseModel):
    hero_id: int # Internal hero ID for that game
    template_slug: str # ID of the hero template
    health: int
    name: str

class GameState(BaseModel):
    turn: int = 1
    active: Literal["side_a", "side_b"] = "side_a"
    phase: Phase = "start"
    event_queue: List[Event] = Field(
        default_factory=lambda: [Event(type="start_turn", player="side_a")]
    )
    # Centralized storage of all cards in the game by their unique ID
    cards: Dict[int, CardInPlay] = Field(default_factory=dict)

    heroes: Dict[str, HeroInPlay]

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

    winner: Literal['side_a', 'side_b', 'none'] = 'none'
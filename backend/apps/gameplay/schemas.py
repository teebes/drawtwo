from typing import Literal, List, Dict
from pydantic import BaseModel, Field


PHASE_ORDER = ['start', 'refresh', 'draw', 'main', 'end']

Phase = Literal['start', 'refresh', 'draw', 'main', 'combat', 'end']


class Action(BaseModel):
    type: str


class PhaseTransitionAction(Action):
    type: str = "phase_transition"
    phase: Phase


class Event(BaseModel):
    type: str
    player: Literal['side_a', 'side_b']
    data: dict = {}


class RefreshEvent(Event):
    type: str = "refresh"

class DrawEvent(Event):
    type: str = "draw_card"


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
    traits: List[Trait] = Field(default_factory=list)


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
    cards: Dict[str, CardInPlay] = Field(default_factory=dict)

    heroes: Dict[str, HeroInPlay]

    board: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "side_a": [],
            "side_b": [],
        }
    )
    hands: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "side_a": [],
            "side_b": [],
        }
    )
    decks: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "side_a": [],
            "side_b": [],
        }
    )
    mana_pool: Dict[str, int] = Field(
        default_factory=lambda: {
            "side_a": 0,
            "side_b": 0,
        }
    )
    mana_used: Dict[str, int] = Field(
        default_factory=lambda: {
            "side_a": 0,
            "side_b": 0,
        }
    )

    winner: Literal['side_a', 'side_b', 'none'] = 'none'


class GameSummary(BaseModel):
    id: int
    name: str


class GameList(BaseModel):
    games: List[GameSummary]


class GameUpdate(BaseModel):
    type: str
    side: Literal['side_a', 'side_b']
    data: dict


class DrawUpdate(GameUpdate):
    type: str = "draw"


class ManaUpdate(GameUpdate):
    type: str = "mana"


class GameUpdates(BaseModel):
    type: str = "game_updates"
    updates: List[GameUpdate]
    state: GameState
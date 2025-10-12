from typing import Literal, List, Dict, Union, Annotated, Literal, Optional
from pydantic import BaseModel, Field, Discriminator

from apps.builder.schemas import (
    Action,
    TitleConfig,
    Trait,
    HeroPower,
)

PHASE_ORDER = ['start', 'refresh', 'draw', 'main',]

Phase = Literal['start', 'refresh', 'draw', 'main', 'combat', 'end']

from apps.gameplay.schemas.effects import Effect


class CardInPlay(BaseModel):
    card_type: Literal['creature', 'spell']
    card_id: str # Interal card ID for that game
    template_slug: str # ID of the card template
    name: str
    description: str = ''
    attack: int = 0
    health: int = 0
    cost: int = 0
    traits: List[Trait] = Field(default_factory=list)
    exhausted: bool = True

    def has_trait(self, trait_code: str) -> bool:
        return any(trait.type == trait_code for trait in self.traits)


class HeroInPlay(BaseModel):
    hero_id: str # Internal hero ID for that game
    template_slug: str # ID of the hero template
    health: int
    name: str
    exhausted: bool = True
    actions: List[Action] = Field(default_factory=list)
    hero_power: HeroPower


class GameState(BaseModel):
    turn: int = 1
    active: Literal["side_a", "side_b"] = "side_a"
    phase: Phase = "start"
    event_queue: List[Dict] = Field(default_factory=list)  # Old system (deprecated)
    queue: list[Effect] = Field(default_factory=list)
    # Centralized storage of all cards in the game by their unique ID
    cards: Dict[str, CardInPlay] = Field(default_factory=dict)

    heroes: Dict[str, HeroInPlay]

    ai_sides: List[Literal['side_a', 'side_b']] = Field(default_factory=list)

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
    graveyard: Dict[str, List[str]] = Field(
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

    config: TitleConfig = Field(default_factory=TitleConfig)

    @property
    def opposite_side(self) -> Literal["side_a", "side_b"]:
        return "side_b" if self.active == "side_a" else "side_a"
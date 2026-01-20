from typing import Literal, List, Dict, Union, Annotated, Literal, Optional
from pydantic import BaseModel, Field, Discriminator, model_validator

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
    art_url: Optional[str] = None

    def has_trait(self, trait_code: str) -> bool:
        return any(trait.type == trait_code for trait in self.traits)


class Creature(BaseModel):
    creature_id: str
    card_id: str
    name: str
    description: str = ''
    attack: int = 0
    attack_max: Optional[int] = None
    health: int = 0
    health_max: Optional[int] = None
    traits: List[Trait] = Field(default_factory=list)
    exhausted: bool = True
    art_url: Optional[str] = None

    @model_validator(mode="after")
    def _set_max_stats(self) -> 'Creature':
        if self.attack_max is None:
            self.attack_max = self.attack
        if self.health_max is None:
            self.health_max = self.health
        return self


class HeroInPlay(BaseModel):
    hero_id: str # Internal hero ID for that game
    template_slug: str # ID of the hero template
    health: int
    health_max: Optional[int] = None
    name: str
    player_name: Optional[str] = None
    description: str = ''
    exhausted: bool = True
    actions: List[Action] = Field(default_factory=list)
    hero_power: HeroPower
    art_url: Optional[str] = None

    @model_validator(mode="after")
    def _set_health_max(self) -> 'HeroInPlay':
        if self.health_max is None:
            self.health_max = self.health
        return self


class GameState(BaseModel):
    turn: int = 1
    active: Literal["side_a", "side_b"] = "side_a"
    phase: Phase = "start"
    event_queue: List[Dict] = Field(default_factory=list)  # Old system (deprecated)
    queue: list[Effect] = Field(default_factory=list)
    # Centralized storage of all cards in the game by their unique ID
    cards: Dict[str, CardInPlay] = Field(default_factory=dict)
    creatures: Dict[str, Creature] = Field(default_factory=dict)
    last_creature_id: int = 0

    heroes: Dict[str, HeroInPlay]

    ai_sides: List[Literal['side_a', 'side_b']] = Field(default_factory=list)

    # Card templates that can be summoned by slug (for summon effects)
    summonable_cards: Dict[str, CardInPlay] = Field(default_factory=dict)

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

    time_per_turn: int = 0
    turn_expires: Optional[str] = None

    @property
    def opposite_side(self) -> Literal["side_a", "side_b"]:
        return "side_b" if self.active == "side_a" else "side_a"


class Notification(BaseModel):
    ref_id: int
    type: Literal[
        'game_friendly',
        'game_challenge',
        'game_ranked',
        'game_ranked_queued',
        'game_pve',
        'friend_request']
    message: str
    is_user_turn: bool | None = None
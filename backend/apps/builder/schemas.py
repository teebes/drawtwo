from pydantic import BaseModel, Field
from typing import Literal, List, Annotated, Union, Optional
from pydantic import Discriminator


class TitleConfig(BaseModel):
    deck_size_limit: int = 30
    deck_card_max_count: int = 9
    hand_start_size: int = 3


class Encounter(BaseModel):
    name: str


# Ingestable data


# Actions

class ActionBase(BaseModel):
    action: str


class DrawAction(ActionBase):
    action: Literal['draw'] = 'draw'
    amount: int = 1


class DamageAction(ActionBase):
    action: Literal['damage'] = 'damage'
    amount: int
    target: Literal['hero', 'creature', 'enemy'] = 'creature'
    scope: Literal['single', 'cleave', 'all'] = 'single'
    damage_type: Literal["physical", "spell"] = "physical"


class HealAction(ActionBase):
    action: Literal['heal'] = 'heal'
    amount: int
    target: Literal['hero', 'creature', 'friendly'] = 'creature'
    scope: Literal['single', 'cleave', 'all'] = 'single'


class RemoveAction(ActionBase):
    action: Literal['remove'] = 'remove'
    target: Literal['creature', 'enemy'] = 'creature'
    scope: Literal['single', 'cleave', 'all'] = 'single'


Action = Annotated[
    Union[DrawAction, DamageAction, HealAction, RemoveAction],
    Discriminator('action')
]


# Traits

class TraitBase(BaseModel):
    type: str
    actions: List[Action] = Field(default_factory=list)


class Charge(TraitBase):
    type: Literal['charge'] = 'charge'


class Ranged(TraitBase):
    type: Literal['ranged'] = 'ranged'


class Taunt(TraitBase):
    type: Literal['taunt'] = 'taunt'


class Battlecry(TraitBase):
    type: Literal['battlecry'] = 'battlecry'


class DeathRattle(TraitBase):
    type: Literal['deathrattle'] = 'deathrattle'


class Stealth(TraitBase):
    type: Literal['stealth'] = 'stealth'


class Unique(TraitBase):
    type: Literal['unique'] = 'unique'

Trait = Annotated[
    Union[Charge, Ranged, Taunt, Battlecry, DeathRattle, Stealth, Unique],
    Discriminator('type')
]


# Deck Script

class DeckScript(BaseModel):
    strategy: Literal['rush', 'control', 'combo', 'aggressive', 'defensive'] = 'rush'


class ResourceBase(BaseModel):
    type: str


class Card(ResourceBase):
    id: Optional[int] = None
    type: Literal['card'] = 'card'
    card_type: Literal['creature', 'spell']
    slug: str
    name: str
    description: Optional[str] = ''
    cost: int
    attack: int = 0
    health: int = 0
    traits: List[Trait] = Field(default_factory=list)
    faction: Optional[str] = None
    art_url: Optional[str] = None  # For future user-uploaded art
    is_collectible: bool = True


class Deck(ResourceBase):
    type: Literal['deck'] = 'deck'
    name: str
    hero: str
    cards: List[dict] = Field(default_factory=list)


class HeroPower(BaseModel):
    name: str = 'Power'
    description: Optional[str] = None
    actions: List[Action] = Field(default_factory=list)


class Hero(ResourceBase):
    type: Literal['hero'] = 'hero'
    slug: str
    name: str
    description: str
    health: int
    hero_power: HeroPower
    faction: Optional[str] = None


Resource = Annotated[
    Union[Card, Deck, Hero],
    Discriminator('type')
]


class IngestedResource(BaseModel):
    """Represents a resource that was created or updated during ingestion."""
    resource_type: Literal['card', 'hero', 'deck']
    action: Literal['created', 'updated']
    id: int
    slug: str
    name: str

import datetime
from typing import Literal, List, Optional

from pydantic import BaseModel


class Trait(BaseModel):
    slug: str
    name: str
    data: dict = {}


class Card(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    card_type: Literal['minion', 'spell']
    cost: int
    attack: int
    health: int
    traits: List[Trait]
    faction: Optional[str] = None


class Hero(BaseModel):
    id: int
    slug: str
    name: str
    health: int
    hero_power: dict = {}
    spec: dict = {}
    faction: Optional[str] = None


class Deck(BaseModel):
    id: int
    name: str
    description: str
    hero: Hero
    card_count: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
from typing import Literal, List, Optional

from pydantic import BaseModel


class Trait(BaseModel):
    slug: str
    name: str
    argument: Optional[int] = None
    extra_data: dict = {}


class Card(BaseModel):
    slug: str
    name: str
    description: str
    card_type: Literal['minion', 'spell']
    cost: int
    attack: int
    health: int
    traits: List[Trait]
    faction: Optional[str] = None
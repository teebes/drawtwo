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


class CardActionBase(BaseModel):
    action: str


class CardActionDraw(CardActionBase):
    action: Literal['draw'] = 'draw'
    amount: int = 1


class CardActionDamage(CardActionBase):
    action: Literal['damage'] = 'damage'
    amount: int
    target: Literal['hero', 'minion', 'enemy'] = 'minion'


CardAction = Annotated[
    Union[CardActionDraw, CardActionDamage],
    Discriminator('action')
]


class TraitBase(BaseModel):
    type: str
    actions: List[CardAction] = Field(default_factory=list)


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


Trait = Annotated[
    Union[Charge, Ranged, Taunt, Battlecry, DeathRattle],
    Discriminator('type')
]


class ResourceBase(BaseModel):
    type: str


class Card(ResourceBase):
    id: Optional[int] = None
    type: Literal['card'] = 'card'
    card_type: Literal['minion', 'spell']
    slug: str
    name: str
    description: str
    cost: int
    attack: int = 0
    health: int = 0
    traits: List[Trait]
    faction: Optional[str] = None


class Deck(ResourceBase):
    type: Literal['deck'] = 'deck'
    name: str
    hero: str
    cards: List[dict] = Field(default_factory=list)


class Hero(ResourceBase):
    type: Literal['hero'] = 'hero'
    slug: str
    name: str
    description: str
    health: int
    hero_power: dict
    faction: Optional[str] = None


Resource = Annotated[
    Union[Card, Deck, Hero],
    Discriminator('type')
]


#
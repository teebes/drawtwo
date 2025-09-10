from pydantic import BaseModel, Field
from typing import Literal, List, Annotated, Union, Optional
from pydantic import Discriminator



class TitleConfig(BaseModel):
    deck_size_limit: int = 30
    deck_card_max_count: int = 9


class Encounter(BaseModel):
    name: str


# Ingestable data


class ActionBase(BaseModel):
    action: str


class DrawCardAction(ActionBase):
    action: Literal['draw_card'] = 'draw_card'
    amount: int


class DamageAction(ActionBase):
    action: Literal['damage'] = 'damage'
    amount: int
    target: Literal['hero', 'minion', 'enemy'] = 'minion'


CardAction = Annotated[
    Union[DrawCardAction, DamageAction],
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


class DeathRattle(TraitBase):
    type: Literal['deathrattle'] = 'deathrattle'


Trait = Annotated[
    Union[Charge, Ranged, Taunt, DeathRattle],
    Discriminator('type')
]


class ResourceBase(BaseModel):
    type: str


class Card(ResourceBase):
    type: Literal['card'] = 'card'
    card_type: Literal['minion', 'spell']
    slug: str
    name: str
    description: str
    cost: int
    attack: int
    health: int
    traits: List[Trait]


Resource = Annotated[
    Union[Card],
    Discriminator('type')
]
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Discriminator, Field


class Encounter(BaseModel):
    name: str


# Ingestable data


# Actions


class ActionBase(BaseModel):
    action: str


class DrawAction(ActionBase):
    action: Literal["draw"] = "draw"
    amount: int = 1


class DamageAction(ActionBase):
    action: Literal["damage"] = "damage"
    amount: int
    target: Literal["hero", "creature", "enemy", "self"] = "creature"
    scope: Literal["single", "cleave", "all"] = "single"
    damage_type: Literal["physical", "spell"] = "spell"


class HealAction(ActionBase):
    action: Literal["heal"] = "heal"
    amount: int
    target: Literal["hero", "creature", "friendly"] = "creature"
    scope: Literal["single", "cleave", "all"] = "single"


class RemoveAction(ActionBase):
    action: Literal["remove"] = "remove"
    target: Literal["creature", "enemy"] = "creature"
    scope: Literal["single", "cleave", "all"] = "single"


class TempManaBoostAction(ActionBase):
    action: Literal["temp_mana_boost"] = "temp_mana_boost"
    amount: int
    target: Literal["hero", "creature", "friendly"] = "hero"


class SummonAction(ActionBase):
    action: Literal["summon"] = "summon"
    target: str


class ClearAction(ActionBase):
    action: Literal["clear"] = "clear"
    target: Literal["both", "own", "opponent"] = "both"


class BuffAction(ActionBase):
    action: Literal["buff"] = "buff"
    attribute: Literal["attack", "health"] = "attack"
    amount: int
    target: Literal["hero", "creature", "friendly"] = "creature"
    scope: Literal["single", "cleave", "all"] = "single"


Action = Annotated[
    Union[
        BuffAction,
        ClearAction,
        DrawAction,
        DamageAction,
        HealAction,
        RemoveAction,
        SummonAction,
        TempManaBoostAction,
    ],
    Discriminator("action"),
]


# Traits


class TraitBase(BaseModel):
    type: str
    actions: List[Action] = Field(default_factory=list)


class Charge(TraitBase):
    type: Literal["charge"] = "charge"


class Ranged(TraitBase):
    type: Literal["ranged"] = "ranged"


class Taunt(TraitBase):
    type: Literal["taunt"] = "taunt"


class Battlecry(TraitBase):
    type: Literal["battlecry"] = "battlecry"


class DeathRattle(TraitBase):
    type: Literal["deathrattle"] = "deathrattle"


class Stealth(TraitBase):
    type: Literal["stealth"] = "stealth"


class Unique(TraitBase):
    type: Literal["unique"] = "unique"


Trait = Annotated[
    Union[Charge, Ranged, Taunt, Battlecry, DeathRattle, Stealth, Unique],
    Discriminator("type"),
]


# Deck Script


class DeckScript(BaseModel):
    strategy: Literal["rush", "control", "combo", "aggressive", "defensive"] = "rush"


# Resources


class ResourceBase(BaseModel):
    type: str


class Card(ResourceBase):
    id: Optional[int] = None
    type: Literal["card"] = "card"
    card_type: Literal["creature", "spell"]
    slug: str
    name: str
    description: Optional[str] = ""
    cost: int
    attack: int = 0
    health: int = 0
    traits: List[Trait] = Field(default_factory=list)
    faction: Optional[str] = None
    art_url: Optional[str] = None  # For future user-uploaded art
    is_collectible: bool = True


class Deck(ResourceBase):
    type: Literal["deck"] = "deck"
    name: str
    hero: str
    cards: List[dict] = Field(default_factory=list)


class HeroPower(BaseModel):
    name: str = "Power"
    description: Optional[str] = None
    actions: List[Action] = Field(default_factory=list)


class Hero(ResourceBase):
    type: Literal["hero"] = "hero"
    slug: str
    name: str
    description: str
    health: int
    hero_power: HeroPower
    faction: Optional[str] = None


class TitleConfig(ResourceBase):
    type: Literal["config"] = "config"
    deck_size_limit: int = 30
    min_cards_in_deck: int = 10
    deck_card_max_count: int = 9
    hand_start_size: int = 3
    side_b_compensation: Optional[str] = None
    death_retaliation: bool = False
    ranked_time_per_turn: int = 60


Resource = Annotated[Union[Card, Deck, Hero, TitleConfig], Discriminator("type")]


class IngestedResource(BaseModel):
    """Represents a resource that was created or updated during ingestion."""

    resource_type: Literal["card", "hero", "deck", "config"]
    action: Literal["created", "updated"]
    id: int
    slug: str
    name: str

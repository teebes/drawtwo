from typing import Annotated, Any, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Discriminator, Field, model_serializer


class Encounter(BaseModel):
    name: str


# Ingestable data


# Actions


class ActionBase(BaseModel):
    action: str


class EventValue(BaseModel):
    event: Literal["amount", "damage", "damage_taken", "healing_done"]
    multiplier: float = 1

    @model_serializer(mode="wrap")
    def serialize_model(self, handler):
        data = handler(self)
        if self.multiplier == 1:
            data.pop("multiplier", None)
        return data


AmountValue = Union[int, EventValue]


class DrawAction(ActionBase):
    action: Literal["draw"] = "draw"
    amount: AmountValue = 1
    spec: Optional[dict[str, Any]] = None


class DamageAction(ActionBase):
    action: Literal["damage"] = "damage"
    amount: AmountValue
    target: Literal["hero", "creature", "enemy", "self", "friendly"] = "creature"
    scope: Literal["single", "cleave", "all"] = "single"
    damage_type: Literal["physical", "spell"] = "spell"


class HealAction(ActionBase):
    action: Literal["heal"] = "heal"
    amount: AmountValue
    target: Literal["hero", "creature", "friendly", "self"] = "creature"
    scope: Literal["single", "cleave", "all"] = "single"


class RemoveAction(ActionBase):
    action: Literal["remove"] = "remove"
    target: Literal["creature", "enemy"] = "creature"
    scope: Literal["single", "cleave", "all"] = "single"


class SilenceAction(ActionBase):
    action: Literal["silence"] = "silence"
    target: Literal["creature", "enemy"] = "creature"
    scope: Literal["single"] = "single"


class TempManaBoostAction(ActionBase):
    action: Literal["temp_mana_boost"] = "temp_mana_boost"
    amount: AmountValue
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
    amount: AmountValue
    target: Literal["hero", "creature", "friendly", "self"] = "creature"
    scope: Literal["single", "cleave", "all"] = "single"


Action = Annotated[
    Union[
        BuffAction,
        ClearAction,
        DrawAction,
        DamageAction,
        HealAction,
        RemoveAction,
        SilenceAction,
        SummonAction,
        TempManaBoostAction,
    ],
    Discriminator("action"),
]


# Traits


class TraitBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    actions: List[Action] = Field(default_factory=list)


class Armor(TraitBase):
    type: Literal["armor"] = "armor"


class Charge(TraitBase):
    type: Literal["charge"] = "charge"


class Cleave(TraitBase):
    type: Literal["cleave"] = "cleave"


class Ranged(TraitBase):
    type: Literal["ranged"] = "ranged"


class Taunt(TraitBase):
    type: Literal["taunt"] = "taunt"


class Battlecry(TraitBase):
    type: Literal["battlecry"] = "battlecry"


class DeathRattle(TraitBase):
    type: Literal["deathrattle"] = "deathrattle"


class Inspire(TraitBase):
    type: Literal["inspire"] = "inspire"


class Lifesteal(TraitBase):
    type: Literal["lifesteal"] = "lifesteal"


class Stealth(TraitBase):
    type: Literal["stealth"] = "stealth"


class Unique(TraitBase):
    type: Literal["unique"] = "unique"


class TriggerEntityFilter(BaseModel):
    kind: Optional[Literal["card", "creature", "hero", "board"]] = None
    controller: Literal["self", "opponent", "any"] = "any"
    self: bool = False
    exclude_self: bool = False
    card_type: Optional[Literal["creature", "spell"]] = None
    template_slug: Optional[str] = None


class TriggerCondition(BaseModel):
    event: Literal[
        "card_played",
        "creature_played",
        "spell_used",
        "damage",
        "heal",
        "creature_death",
        "hero_power_used",
    ]
    source: TriggerEntityFilter = Field(default_factory=TriggerEntityFilter)
    target: TriggerEntityFilter = Field(default_factory=TriggerEntityFilter)


class Triggered(TraitBase):
    type: Literal["triggered"] = "triggered"
    when: TriggerCondition


Trait = Annotated[
    Union[
        Armor,
        Battlecry,
        Charge,
        Cleave,
        DeathRattle,
        Inspire,
        Lifesteal,
        Ranged,
        Stealth,
        Taunt,
        Triggered,
        Unique,
    ],
    Discriminator("type"),
]


# Deck Script


class DeckScript(BaseModel):
    strategy: Literal[
        "rush", "control", "combo", "aggressive", "defensive", "smart"
    ] = "rush"
    opening: List[dict] = Field(default_factory=list)


# Resources


class ResourceBase(BaseModel):
    type: str


class TitleMetadata(ResourceBase):
    type: Literal["title"] = "title"
    slug: str
    name: str
    description: str = ""


class FactionResource(ResourceBase):
    type: Literal["faction"] = "faction"
    slug: str
    name: str
    description: str = ""


class TagResource(ResourceBase):
    type: Literal["tag"] = "tag"
    slug: str
    name: str
    description: str = ""


class TraitOverrideResource(ResourceBase):
    type: Literal["trait_override"] = "trait_override"
    slug: str
    name: str
    description: str = ""


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
    spec: dict = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    art_url: Optional[str] = None  # For future user-uploaded art
    is_collectible: bool = True
    hero_slugs: List[str] = Field(default_factory=list)


class Deck(ResourceBase):
    type: Literal["deck"] = "deck"
    name: str
    hero: str
    cards: List[dict] = Field(default_factory=list)


class HeroPower(BaseModel):
    name: str = "Power"
    description: Optional[str] = None
    cost: int = Field(default=0, ge=0)
    actions: List[Action] = Field(default_factory=list)


class Hero(ResourceBase):
    type: Literal["hero"] = "hero"
    slug: str
    name: str
    description: str
    health: int
    hero_power: HeroPower
    faction: Optional[str] = None
    spec: dict = Field(default_factory=dict)


class TitleConfig(ResourceBase):
    type: Literal["config"] = "config"
    deck_size_limit: int = 30
    min_cards_in_deck: int = 10
    deck_card_max_count: int = 9
    hand_start_size: int = 3
    side_b_compensation: Optional[str] = None
    death_retaliation: bool = False
    ranked_time_per_turn: int = 60


Resource = Annotated[
    Union[
        Card,
        Deck,
        FactionResource,
        Hero,
        TagResource,
        TitleConfig,
        TitleMetadata,
        TraitOverrideResource,
    ],
    Discriminator("type"),
]


class IngestedResource(BaseModel):
    """Represents a resource that was created or updated during ingestion."""

    resource_type: Literal[
        "card",
        "config",
        "deck",
        "faction",
        "hero",
        "tag",
        "title",
        "trait_override",
    ]
    action: Literal["created", "updated"]
    id: int
    slug: str
    name: str

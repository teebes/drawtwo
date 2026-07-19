from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Discriminator, Field

from apps.builder.schemas import DeckScript
from apps.gameplay.schemas.game import Creature


class EventBase(BaseModel):
    type: str
    side: Literal["side_a", "side_b"]


class DamageEvent(EventBase):
    type: Literal["event_damage"] = "event_damage"
    damage_type: Literal["physical", "spell"] = "physical"
    source_type: Literal["card", "hero", "board", "creature"] = "card"
    source_id: str
    source_side: Optional[Literal["side_a", "side_b"]] = None
    target_type: Literal["card", "hero", "creature"] = "card"
    target_id: str
    target_side: Optional[Literal["side_a", "side_b"]] = None
    damage: int
    damage_taken: Optional[int] = None
    target_creature: Optional[Creature] = None
    # Whether the target should attempt to retaliate. Mostly used to disable
    # retaliation in the case of retaliation to avoid an infinite loop.
    retaliate: bool = True
    is_retaliation: bool = False


class DrawEvent(EventBase):
    type: Literal["event_draw"] = "event_draw"
    card_id: str
    target_type: Literal["card"] = "card"
    target_id: str


class HealEvent(EventBase):
    type: Literal["event_heal"] = "event_heal"
    source_type: Literal["card", "hero", "board", "creature"] = "card"
    source_id: str
    source_side: Optional[Literal["side_a", "side_b"]] = None
    target_type: Literal["card", "hero", "creature"] = "card"
    target_id: str
    target_side: Optional[Literal["side_a", "side_b"]] = None
    amount: int
    healing_done: Optional[int] = None


class EndTurnEvent(EventBase):
    type: Literal["event_end_turn"] = "event_end_turn"


class GameOverEvent(EventBase):
    type: Literal["event_game_over"] = "event_game_over"
    winner: Literal["side_a", "side_b"]


class NewPhaseEvent(EventBase):
    type: Literal["event_phase"] = "event_phase"
    phase: str


class MulliganEvent(EventBase):
    type: Literal["event_mulligan"] = "event_mulligan"
    card_ids: list[str] = Field(default_factory=list)


# Actionable Events


class ActionableEvent(EventBase):
    source_type: Literal["card", "hero", "board", "creature"] = "card"
    source_id: str
    target_type: Optional[Literal["card", "hero", "creature"]] = "card"
    target_id: Optional[str] = None


class PlayEvent(ActionableEvent):
    type: Literal["event_play"] = "event_play"
    source_type: Literal["card"] = "card"
    position: int
    target_type: Optional[Literal["card", "hero", "creature"]] = None
    target_id: Optional[str] = None
    creature_id: Optional[str] = None


class UseHeroEvent(ActionableEvent):
    type: Literal["event_use_hero"] = "event_use_hero"
    source_type: Literal["hero"] = "hero"


class CreatureDeathEvent(ActionableEvent):
    """
    A creature on the board is killed.
    * source_type / source_id: The creature that caused the death
    * target_type / target_id: The creature that was killed
    * creature: data snapshot of the creature that was killed
    """

    type: Literal["event_creature_death"] = "event_creature_death"
    source_side: Optional[Literal["side_a", "side_b"]] = None
    creature: Creature


class RemoveEvent(EventBase):
    """
    A creature is removed from the board without triggering death effects.
    """

    type: Literal["event_remove"] = "event_remove"
    source_type: Literal["card", "hero", "board", "creature"] = "creature"
    source_id: str
    target_type: Literal["creature"] = "creature"
    target_id: str


class SilenceEvent(EventBase):
    type: Literal["event_silence"] = "event_silence"
    source_type: Literal["card", "hero", "creature", "board"] = "card"
    source_id: str
    target_type: Literal["creature"] = "creature"
    target_id: str
    removed_traits: list[Literal["deathrattle", "triggered"]] = Field(
        default_factory=list
    )


class TempManaBoostEvent(EventBase):
    type: Literal["event_temp_mana_boost"] = "event_temp_mana_boost"
    amount: int


class SummonEvent(EventBase):
    type: Literal["event_summon"] = "event_summon"
    source_type: Literal["card", "hero", "board", "creature"] = "card"
    source_id: str
    target_type: Literal["card"] = "card"
    target_id: str


class ClearEvent(EventBase):
    type: Literal["event_clear"] = "event_clear"
    source_type: Literal["card", "hero"] = "card"
    source_id: str
    target: Literal["both", "own", "opponent"] = "both"


class BuffEvent(EventBase):
    type: Literal["event_buff"] = "event_buff"
    source_type: Literal["card", "hero", "creature"] = "creature"
    source_id: str
    target_type: Literal["creature", "hero"] = "creature"
    target_id: str
    attribute: Literal["attack", "health"] = "attack"
    amount: int


Event = Annotated[
    Union[
        BuffEvent,
        ClearEvent,
        CreatureDeathEvent,
        DamageEvent,
        DrawEvent,
        EndTurnEvent,
        GameOverEvent,
        HealEvent,
        MulliganEvent,
        NewPhaseEvent,
        PlayEvent,
        RemoveEvent,
        SilenceEvent,
        SummonEvent,
        TempManaBoostEvent,
        UseHeroEvent,
    ],
    Discriminator("type"),
]

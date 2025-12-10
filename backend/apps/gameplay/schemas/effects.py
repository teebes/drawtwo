from typing import Literal, Annotated, Union, Optional
from pydantic import BaseModel, Discriminator, Field

from apps.builder.schemas import DeckScript


class EffectBase(BaseModel):
    type: str
    side: Literal['side_a', 'side_b']


class ActionSourceEffect(EffectBase):
    """
    Base class for effects that trigger actions (battlecry, spells, hero powers).
    Provides common fields needed by action handlers to generate child effects.
    """
    source_type: Literal["card", "hero"]
    source_id: str
    target_type: Optional[Literal["creature", "card", "hero"]] = None
    target_id: Optional[str] = None


# ==== Internal State Effects ====

class StartGameEffect(EffectBase):
    type: Literal["effect_start_game"] = "effect_start_game"


class NewPhaseEffect(EffectBase):
    type: Literal["effect_phase"] = "effect_phase"
    phase: Literal["start", "refresh", "draw", "main"]


class EndTurnEffect(EffectBase):
    type: Literal["effect_end_turn"] = "effect_end_turn"


# ==== Command / Action driven Effects ====

class DamageEffect(EffectBase):
    type: Literal["effect_damage"] = "effect_damage"
    damage_type: Literal["physical", "spell"] = "physical"
    source_type: Literal["card", "creature", "hero", "board"] = "creature"
    source_id: str
    target_type: Literal["card", "hero", "creature"] = "card"
    target_id: str
    damage: int
    # Whether the target should attempt to retaliate. Mostly used to disable
    # retaliation in the case of retaliation to avoid an infinite loop.
    retaliate: bool = True


class CardRetaliationEffect(EffectBase):
    type: Literal["effect_card_retaliation"] = "effect_card_retaliation"
    card_id: str
    target_id: str


class DrawEffect(EffectBase):
    type: Literal["effect_draw"] = "effect_draw"
    amount: int = 1


class HealEffect(EffectBase):
    type: Literal["effect_heal"] = "effect_heal"
    source_type: Literal["card", "creature", "hero", "board"] = "creature"
    source_id: str
    target_type: Literal["card", "hero", "creature"] = "card"
    target_id: str
    amount: int


class PlayEffect(ActionSourceEffect):
    type: Literal["effect_play"] = "effect_play"
    source_type: Literal["card"] = "card"  # Playing a card
    position: int
    # source_id (card_id), target_type, and target_id inherited from ActionSourceEffect


class AttackEffect(EffectBase):
    type: Literal["effect_attack"] = "effect_attack"
    card_id: str
    target_type: Literal["card", "hero", "creature"] = "hero"
    target_id: str


class CastEffect(EffectBase):
    type: Literal["effect_cast"] = "effect_cast"
    card_id: str
    target_type: Literal["card", "hero", "creature"] = "hero"
    target_id: str


class UseHeroEffect(ActionSourceEffect):
    type: Literal["effect_use_hero"] = "effect_use_hero"
    source_type: Literal["hero"] = "hero"  # Using hero power
    # source_id (hero_id), target_type, and target_id inherited from ActionSourceEffect


class CastSpellEffect(ActionSourceEffect):
    type: Literal["effect_cast_spell"] = "effect_cast_spell"
    source_type: Literal["card"] = "card"  # Casting a spell card
    # source_id (card_id), target_type, and target_id inherited from ActionSourceEffect


class MarkExhaustedEffect(EffectBase):
    type: Literal["effect_mark_exhausted"] = "effect_mark_exhausted"
    target_type: Literal["card", "creature", "hero"] = "card"
    target_id: str


class RemoveEffect(EffectBase):
    type: Literal["effect_remove"] = "effect_remove"
    source_type: Literal["card", "creature", "hero", "board"] = "creature"
    source_id: str
    target_type: Literal["creature"] = "creature"
    target_id: str


class TempManaBoostEffect(EffectBase):
    type: Literal["effect_temp_mana_boost"] = "effect_temp_mana_boost"
    source_type: Literal["card"] = "card"
    source_id: str
    amount: int


Effect = Annotated[
    Union[
        AttackEffect,
        CastEffect,
        DamageEffect,
        DrawEffect,
        EndTurnEffect,
        HealEffect,
        MarkExhaustedEffect,
        NewPhaseEffect,
        PlayEffect,
        RemoveEffect,
        StartGameEffect,
        TempManaBoostEffect,
        UseHeroEffect,
    ],
    Discriminator('type')
]

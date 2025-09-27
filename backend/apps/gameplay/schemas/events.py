from typing import Literal, Annotated, Union, Optional
from pydantic import BaseModel, Discriminator, Field

from apps.builder.schemas import DeckScript


# ==== Events ====

class EventBase(BaseModel):
    type: str
    side: Literal['side_a', 'side_b']


class StartGameEvent(EventBase):
    type: Literal["event_start_game"] = "event_start_game"


class RefreshPhaseEvent(EventBase):
    type: Literal["event_refresh_phase"] = "event_refresh_phase"


class DrawPhaseEvent(EventBase):
    type: Literal["event_draw_phase"] = "event_draw_phase"


class MainPhaseEvent(EventBase):
    type: Literal["event_main_phase"] = "event_main_phase"


class EndTurnEvent(EventBase):
    type: Literal["event_end_turn"] = "event_end_turn"


class DrawCardEvent(EventBase):
    type: Literal["event_draw_card"] = "event_draw_card"


class PlayCardEvent(EventBase):
    type: Literal["event_play_card"] = "event_play_card"
    card_id: str
    position: int
    target_type: Optional[Literal["card", "hero"]] = None
    target_id: Optional[str] = None


class UseCardEvent(EventBase):
    type: Literal["event_use_card"] = "event_use_card"
    card_id: str
    target_type: Literal["card", "hero"] = "card"
    target_id: str


class CastSpellEvent(EventBase):
    type: Literal["event_cast_spell"] = "event_cast_spell"
    card_id: str
    target_type: Literal["card", "hero"] = "card"
    target_id: str


class DealDamageEvent(EventBase):
    type: Literal["event_damage"] = "event_damage"
    damage_type: Literal["physical", "spell"] = "physical"
    source_type: Literal["card", "hero", "board"] = "card"
    source_id: str
    target_type: Literal["card", "hero",] = "card"
    target_id: str
    damage: int
    # Whether the target should attempt to retaliate. Mostly used to disable
    # retaliation in the case of retaliation to avoid an infinite loop.
    retaliate: bool = True


class CardRetaliationEvent(EventBase):
    type: Literal["event_card_retaliation"] = "event_card_retaliation"
    card_id: str
    target_id: str


class ChooseAIMoveEvent(EventBase):
    type: Literal["event_choose_ai_move"] = "event_choose_ai_move"
    side: Literal['side_a', 'side_b']
    script: Optional[DeckScript] = Field(default_factory=DeckScript)


class NewTurnEvent(EventBase):
    type: Literal["event_new_turn"] = "event_new_turn"


class GameOverEvent(EventBase):
    type: Literal["event_game_over"] = "event_game_over"
    winner: Literal["side_a", "side_b"]


GameEvent = Annotated[
    Union[
        StartGameEvent,
        CardRetaliationEvent,
        ChooseAIMoveEvent,
        DealDamageEvent,
        DrawPhaseEvent,
        EndTurnEvent,
        GameOverEvent,
        MainPhaseEvent,
        DrawCardEvent,
        PlayCardEvent,
        RefreshPhaseEvent,
        UseCardEvent],
    Discriminator('type')
]

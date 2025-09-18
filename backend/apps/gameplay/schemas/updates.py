from typing import Literal, Annotated, Union
from pydantic import BaseModel, Discriminator



class UpdateBase(BaseModel):
    type: Literal["update"] = "update"
    side: Literal['side_a', 'side_b']


class RefreshPhaseUpdate(UpdateBase):
    type: Literal["update_refresh_phase"] = "update_refresh_phase"


class DrawPhaseUpdate(UpdateBase):
    type: Literal["update_draw_phase"] = "update_draw_phase"


class MainPhaseUpdate(UpdateBase):
    type: Literal["update_main_phase"] = "update_main_phase"


class EndTurnUpdate(UpdateBase):
    type: Literal["update_end_turn"] = "update_end_turn"


class DrawCardUpdate(UpdateBase):
    type: Literal["update_draw_card"] = "update_draw_card"
    card_id: str


class PlayCardUpdate(UpdateBase):
    type: Literal["update_play_card"] = "update_play_card"
    card_id: str
    position: int


class DealDamageUpdate(UpdateBase):
    type: Literal["update_deal_damage"] = "update_deal_damage"
    source_type: Literal["card", "hero", "board"] = "card"
    source_id: str
    target_type: Literal["card", "hero",] = "card"
    target_id: str
    damage: int


class HeroDamageUpdate(UpdateBase):
    type: Literal["update_hero_damage"] = "update_hero_damage"
    hero_id: str
    damage: int


class CardDamageUpdate(UpdateBase):
    type: Literal["update_card_damage"] = "update_card_damage"
    card_id: str
    damage: int


class CardDestroyedUpdate(UpdateBase):
    type: Literal["update_card_destroyed"] = "update_card_destroyed"
    card_id: str


class GameOverUpdate(UpdateBase):
    type: Literal["update_game_over"] = "update_game_over"
    winner: Literal["side_a", "side_b"]


GameUpdate = Annotated[
    Union[
        CardDamageUpdate,
        CardDestroyedUpdate,
        HeroDamageUpdate,
        DrawPhaseUpdate,
        EndTurnUpdate,
        GameOverUpdate,
        MainPhaseUpdate,
        DrawCardUpdate,
        PlayCardUpdate,
        RefreshPhaseUpdate,
        ],
    Discriminator('type')
]

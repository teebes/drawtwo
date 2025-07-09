from typing import Literal, List, Dict, Union, Annotated
from pydantic import BaseModel, Field, Discriminator


PHASE_ORDER = ['start', 'refresh', 'draw', 'main',]

Phase = Literal['start', 'refresh', 'draw', 'main', 'combat', 'end']


class ActionBase(BaseModel):
    type: str


class PlayCardAction(ActionBase):
    type: Literal["play_card_action"] = "play_card_action"
    card_id: str
    position: int


class UseCardAction(ActionBase):
    type: Literal["use_card_action"] = "use_card_action"
    card_id: str
    target_type: Literal["card", "hero"] = "card"
    target_id: str


class EndTurnAction(ActionBase):
    type: Literal["end_turn_action"] = "end_turn_action"


GameAction = Annotated[
    Union[PlayCardAction, UseCardAction, EndTurnAction],
    Discriminator('type')]


# ==== Events ====

class EventBase(BaseModel):
    type: str
    side: Literal['side_a', 'side_b']


class RefreshPhaseEvent(EventBase):
    type: Literal["refresh_phase_event"] = "refresh_phase_event"


class DrawPhaseEvent(EventBase):
    type: Literal["draw_phase_event"] = "draw_phase_event"


class MainPhaseEvent(EventBase):
    type: Literal["main_phase_event"] = "main_phase_event"


class EndTurnEvent(EventBase):
    type: Literal["end_turn_event"] = "end_turn_event"


class PlayCardEvent(EventBase):
    type: Literal["play_card_event"] = "play_card_event"
    card_id: str
    position: int


class UseCardEvent(EventBase):
    type: Literal["use_card_event"] = "use_card_event"
    card_id: str
    target_type: Literal["card", "hero"] = "card"
    target_id: str


class CardRetaliationEvent(EventBase):
    type: Literal["card_retaliation_event"] = "card_retaliation_event"
    card_id: str
    target_id: str


class NewTurnEvent(EventBase):
    type: Literal["end_turn"] = "new_turn"


GameEvent = Annotated[
    Union[
        CardRetaliationEvent,
        EndTurnEvent,
        DrawPhaseEvent,
        MainPhaseEvent,
        PlayCardEvent,
        RefreshPhaseEvent,
        UseCardEvent],
    Discriminator('type')
]


# ==== Game State ====


class Trait(BaseModel):
    slug: str
    name: str
    data: dict = {}


class CardInPlay(BaseModel):
    card_type: Literal['minion', 'spell']
    card_id: str # Interal card ID for that game
    template_slug: str # ID of the card template
    attack: int
    health: int
    cost: int
    traits: List[Trait] = Field(default_factory=list)
    exhausted: bool = True


class HeroInPlay(BaseModel):
    hero_id: int # Internal hero ID for that game
    template_slug: str # ID of the hero template
    health: int
    name: str


class GameState(BaseModel):
    turn: int = 1
    active: Literal["side_a", "side_b"] = "side_a"
    phase: Phase = "start"
    event_queue: List[GameEvent] = Field(default_factory=list)
    # Centralized storage of all cards in the game by their unique ID
    cards: Dict[str, CardInPlay] = Field(default_factory=dict)

    heroes: Dict[str, HeroInPlay]

    board: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "side_a": [],
            "side_b": [],
        }
    )
    hands: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "side_a": [],
            "side_b": [],
        }
    )
    decks: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "side_a": [],
            "side_b": [],
        }
    )
    mana_pool: Dict[str, int] = Field(
        default_factory=lambda: {
            "side_a": 0,
            "side_b": 0,
        }
    )
    mana_used: Dict[str, int] = Field(
        default_factory=lambda: {
            "side_a": 0,
            "side_b": 0,
        }
    )

    winner: Literal['side_a', 'side_b', 'none'] = 'none'


class GameSummary(BaseModel):
    id: int
    name: str


class GameList(BaseModel):
    games: List[GameSummary]


# ==== Updates ====


class UpdateBase(BaseModel):
    type: Literal["game_update"] = "game_update"
    side: Literal['side_a', 'side_b']


class RefreshPhaseUpdate(UpdateBase):
    type: Literal["refresh_phase_update"] = "refresh_phase_update"


class DrawPhaseUpdate(UpdateBase):
    type: Literal["draw_phase_update"] = "draw_phase_update"


class MainPhaseUpdate(UpdateBase):
    type: Literal["main_phase_update"] = "main_phase_update"


class EndTurnUpdate(UpdateBase):
    type: Literal["end_turn_update"] = "end_turn_update"


class PlayCardUpdate(UpdateBase):
    type: Literal["play_card_update"] = "play_card_update"
    card_id: str
    position: int


class HeroDamageUpdate(UpdateBase):
    type: Literal["hero_damage_update"] = "hero_damage_update"
    hero_id: str
    damage: int


class CardDamageUpdate(UpdateBase):
    type: Literal["card_damage_update"] = "card_damage_update"
    card_id: str
    damage: int


class CardDestroyedUpdate(UpdateBase):
    type: Literal["card_destroyed_update"] = "card_destroyed_update"
    card_id: str


class GameOverUpdate(UpdateBase):
    type: Literal["game_over_update"] = "game_over_update"
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
        PlayCardUpdate,
        RefreshPhaseUpdate,
        ],
    Discriminator('type')
]


class GameUpdates(BaseModel):
    type: Literal["game_updates"] = "game_updates"
    updates: List[GameUpdate]
    state: GameState


class ResolvedEvent(BaseModel):
    state: GameState
    updates: list[GameUpdate]
    events: list[GameEvent]

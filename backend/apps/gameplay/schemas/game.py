import hashlib
import random
import uuid
from typing import Annotated, Dict, List, Literal, Optional, TypeVar, Union

from pydantic import BaseModel, Discriminator, Field, model_validator

from apps.builder.schemas import Action, HeroPower, TitleConfig, Trait

PHASE_ORDER = [
    "mulligan",
    "start",
    "refresh",
    "draw",
    "main",
]

Phase = Literal["mulligan", "start", "refresh", "draw", "main", "combat", "end"]

from apps.gameplay.schemas.effects import Effect


class CardInPlay(BaseModel):
    card_type: Literal["creature", "spell"]
    card_id: str  # Interal card ID for that game
    template_slug: str  # ID of the card template
    name: str
    description: str = ""
    attack: int = 0
    health: int = 0
    cost: int = 0
    traits: List[Trait] = Field(default_factory=list)
    exhausted: bool = True
    art_url: Optional[str] = None

    def has_trait(self, trait_code: str) -> bool:
        return any(trait.type == trait_code for trait in self.traits)


class Creature(BaseModel):
    creature_id: str
    card_id: str
    name: str
    description: str = ""
    attack: int = 0
    attack_max: Optional[int] = None
    health: int = 0
    health_max: Optional[int] = None
    traits: List[Trait] = Field(default_factory=list)
    exhausted: bool = True
    art_url: Optional[str] = None

    @model_validator(mode="after")
    def _set_max_stats(self) -> "Creature":
        if self.attack_max is None:
            self.attack_max = self.attack
        if self.health_max is None:
            self.health_max = self.health
        return self


class HeroInPlay(BaseModel):
    hero_id: str  # Internal hero ID for that game
    template_slug: str  # ID of the hero template
    health: int
    health_max: Optional[int] = None
    name: str
    player_name: Optional[str] = None
    description: str = ""
    exhausted: bool = True
    actions: List[Action] = Field(default_factory=list)
    hero_power: HeroPower
    art_url: Optional[str] = None

    @model_validator(mode="after")
    def _set_health_max(self) -> "HeroInPlay":
        if self.health_max is None:
            self.health_max = self.health
        return self


class GameState(BaseModel):
    turn: int = 1
    active: Literal["side_a", "side_b"] = "side_a"
    phase: Phase = "start"
    event_queue: List[Dict] = Field(default_factory=list)  # Old system (deprecated)
    queue: list[Effect] = Field(default_factory=list)
    # Centralized storage of all cards in the game by their unique ID
    cards: Dict[str, CardInPlay] = Field(default_factory=dict)
    creatures: Dict[str, Creature] = Field(default_factory=dict)
    last_creature_id: int = 0

    heroes: Dict[str, HeroInPlay]

    ai_sides: List[Literal["side_a", "side_b"]] = Field(default_factory=list)
    opening_hand_sizes: Dict[Literal["side_a", "side_b"], int] = Field(
        default_factory=dict
    )

    # Card templates that can be summoned by slug (for summon effects)
    summonable_cards: Dict[str, CardInPlay] = Field(default_factory=dict)

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
    mulligan_done: Dict[str, bool] = Field(
        default_factory=lambda: {
            "side_a": False,
            "side_b": False,
        }
    )
    mulligan_options: Dict[str, List[str]] = Field(
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
    graveyard: Dict[str, List[str]] = Field(
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

    winner: Literal["side_a", "side_b", "none"] = "none"

    config: TitleConfig = Field(default_factory=TitleConfig)

    time_per_turn: int = 0
    turn_expires: Optional[str] = None

    rng_seed: str = Field(default_factory=lambda: uuid.uuid4().hex)
    rng_counter: int = 0

    @property
    def opposite_side(self) -> Literal["side_a", "side_b"]:
        return "side_b" if self.active == "side_a" else "side_a"

    def next_rng(self, purpose: str = "") -> random.Random:
        """
        Return a deterministic RNG stream for the next stochastic engine action.

        The seed and counter live in GameState so self-play and replay
        verification can reproduce deck shuffles and other random choices
        without storing Python's non-JSON-serializable RNG state.
        """
        material = f"{self.rng_seed}:{self.rng_counter}:{purpose}"
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        self.rng_counter += 1
        return random.Random(int(digest, 16))

    def shuffle_in_place(self, items: list, purpose: str = "") -> None:
        self.next_rng(purpose).shuffle(items)


T = TypeVar("T")


def deterministic_choice(state: GameState, items: list[T], purpose: str = "") -> T:
    """
    Deterministically choose an item for policy tie-breaks without advancing
    engine RNG state.
    """
    item_material = "|".join(
        item.model_dump_json() if hasattr(item, "model_dump_json") else repr(item)
        for item in items
    )
    material = (
        f"{state.rng_seed}:{state.rng_counter}:{purpose}:"
        f"{len(items)}:{item_material}"
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return items[int(digest, 16) % len(items)]


class Notification(BaseModel):
    ref_id: int
    type: Literal[
        "game_friendly",
        "game_challenge",
        "game_ranked",
        "game_ranked_queued",
        "game_ended",
        "game_pve",
        "friend_request",
    ]
    message: str
    is_user_turn: bool | None = None

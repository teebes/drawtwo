from typing import List, Literal

from pydantic import BaseModel


class GameSummary(BaseModel):
    id: int
    name: str
    type: Literal["pve", "ranked", "friendly", "intro"]
    ladder_type: Literal["rapid", "daily"] | None = None
    is_user_turn: bool


class GameList(BaseModel):
    games: List[GameSummary]

from typing import List
from pydantic import BaseModel


class GameSummary(BaseModel):
    id: int
    name: str


class GameList(BaseModel):
    games: List[GameSummary]

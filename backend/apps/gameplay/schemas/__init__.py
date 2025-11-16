from typing import List, Literal
from pydantic import BaseModel


class GameSummary(BaseModel):
    id: int
    name: str
    type: Literal['pve', 'pvp']


class GameList(BaseModel):
    games: List[GameSummary]

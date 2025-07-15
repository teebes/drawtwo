from pydantic import BaseModel


class TitleConfig(BaseModel):
    deck_size_limit: int = 30
    deck_card_max_count: int = 9

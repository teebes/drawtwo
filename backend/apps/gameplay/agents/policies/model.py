from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from ai.data.replays import command_key
from ai.models.linear_policy import LinearPolicyModel
from apps.gameplay.agents.observation import make_observation
from apps.gameplay.schemas.commands import Command
from apps.gameplay.schemas.game import GameState

logger = logging.getLogger(__name__)


def resolve_model_path(model_path: str) -> Path:
    path = Path(model_path).expanduser()
    if path.is_absolute():
        return path
    return Path(settings.BASE_DIR) / path


@lru_cache(maxsize=8)
def _load_model(path: str, mtime_ns: int) -> LinearPolicyModel:
    # mtime_ns is part of the cache key so replacing a checkpoint reloads it.
    return LinearPolicyModel.load(path)


class LinearModelPolicy:
    """Live-game adapter for the local linear command-ranking checkpoint."""

    def __init__(self, model_path: str):
        self.model_path = resolve_model_path(model_path)

    def _model(self) -> LinearPolicyModel:
        stat = self.model_path.stat()
        return _load_model(str(self.model_path), stat.st_mtime_ns)

    def select_command(
        self,
        state: GameState,
        legal_commands: list[Command],
        budget_ms: int = 100,
    ) -> Command | None:
        if not legal_commands:
            return None

        observation = make_observation(state, state.active).model_dump(mode="json")
        selected = self._model().select_command(
            observation,
            state.active,
            legal_commands,
        )
        if selected is None:
            return None

        selected_key = command_key(selected)
        for legal_command in legal_commands:
            if command_key(legal_command) == selected_key:
                return legal_command

        logger.warning(
            "Linear model selected a command outside the legal-command list: %s",
            selected,
        )
        return None

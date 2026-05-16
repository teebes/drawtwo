from apps.gameplay.schemas.commands import Command
from apps.gameplay.schemas.game import GameState, deterministic_choice


class RandomLegalPolicy:
    """Choose uniformly from legal commands."""

    def select_command(
        self,
        state: GameState,
        legal_commands: list[Command],
        budget_ms: int = 100,
    ) -> Command | None:
        if not legal_commands:
            return None
        return deterministic_choice(state, legal_commands, "random_legal_policy")

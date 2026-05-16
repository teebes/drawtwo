from apps.builder.schemas import DeckScript
from apps.gameplay.agents.legal import list_legal_commands
from apps.gameplay.agents.policies.scripted import ScriptedPolicy
from apps.gameplay.schemas.commands import Command, EndTurnCommand
from apps.gameplay.schemas.effects import Effect
from apps.gameplay.schemas.game import GameState


class AIMoveChooser:
    """Compatibility facade for the built-in scripted AI opponent."""

    @staticmethod
    def choose_command(state: GameState, script: DeckScript) -> Command | None:
        legal_commands = list_legal_commands(state, state.active)
        return ScriptedPolicy(script).select_command(state, legal_commands)

    @staticmethod
    def choose_move(state: GameState, script: DeckScript) -> Effect | None:
        """
        Legacy API used by older tests.

        New AI plumbing should use `choose_command` so bots submit the same
        command vocabulary as human clients.
        """
        from apps.gameplay.services import GameService

        command = AIMoveChooser.choose_command(state, script)
        if not command:
            return None
        if isinstance(command, EndTurnCommand):
            return None
        effects = GameService.compile_cmd(
            state,
            command.model_dump(mode="json"),
            state.active,
        )
        return effects[0] if effects else None

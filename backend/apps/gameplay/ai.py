import logging
from dataclasses import dataclass
from typing import Any

from apps.builder.schemas import DeckScript
from apps.gameplay.agents.legal import list_legal_commands
from apps.gameplay.agents.policies.scripted import ScriptedPolicy
from apps.gameplay.schemas.commands import Command, EndTurnCommand
from apps.gameplay.schemas.effects import Effect
from apps.gameplay.schemas.game import GameState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AIDecision:
    command: Command | None
    actor_kind: str
    policy: str
    error: str = ""


class AIMoveChooser:
    """Compatibility facade for the built-in scripted AI opponent."""

    @staticmethod
    def _strategy_config(deck) -> dict[str, Any]:
        ai_player = getattr(deck, "ai_player", None)
        if not ai_player:
            return {}
        config = ai_player.strategy_config or {}
        return dict(config) if isinstance(config, dict) else {}

    @staticmethod
    def _policy_kind(deck) -> str:
        config = AIMoveChooser._strategy_config(deck)
        return str(
            config.get("policy")
            or config.get("policy_kind")
            or config.get("kind")
            or "scripted"
        )

    @staticmethod
    def actor_kind_for_deck(deck) -> str:
        return (
            "model_ai"
            if AIMoveChooser._policy_kind(deck) in {"linear_model", "model"}
            else "scripted_ai"
        )

    @staticmethod
    def choose_command(state: GameState, script: DeckScript) -> Command | None:
        legal_commands = list_legal_commands(state, state.active)
        return ScriptedPolicy(script).select_command(state, legal_commands)

    @staticmethod
    def _scripted_decision(
        state: GameState,
        deck,
        legal_commands: list[Command],
        *,
        policy: str = "scripted",
        error: str = "",
    ) -> AIDecision:
        script = DeckScript.model_validate(deck.script or {})
        command = ScriptedPolicy(script).select_command(state, legal_commands)
        return AIDecision(
            command=command,
            actor_kind="scripted_ai",
            policy=policy,
            error=error,
        )

    @staticmethod
    def choose_decision(state: GameState, deck) -> AIDecision:
        legal_commands = list_legal_commands(state, state.active)
        config = AIMoveChooser._strategy_config(deck)
        policy_kind = AIMoveChooser._policy_kind(deck)

        if policy_kind in {"linear_model", "model"}:
            model_path = config.get("model_path")
            if model_path:
                try:
                    from apps.gameplay.agents.policies.model import LinearModelPolicy

                    command = LinearModelPolicy(str(model_path)).select_command(
                        state,
                        legal_commands,
                    )
                    return AIDecision(
                        command=command,
                        actor_kind="model_ai",
                        policy=f"linear_model:{model_path}",
                    )
                except Exception as exc:
                    logger.warning("Model AI failed; falling back to scripted: %s", exc)
                    return AIMoveChooser._scripted_decision(
                        state,
                        deck,
                        legal_commands,
                        policy=f"scripted_fallback:linear_model:{model_path}",
                        error=str(exc),
                    )

            logger.warning("Model AI configured without model_path; using scripted")
            return AIMoveChooser._scripted_decision(
                state,
                deck,
                legal_commands,
                policy="scripted_fallback:missing_model_path",
                error="missing model_path",
            )

        return AIMoveChooser._scripted_decision(
            state,
            deck,
            legal_commands,
        )

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

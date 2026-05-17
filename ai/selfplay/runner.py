from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai.data.replays import command_key, to_command_dict


def setup_django() -> None:
    repo_or_backend = Path(__file__).resolve().parents[2]
    backend_dir = repo_or_backend / "backend"
    if (backend_dir / "manage.py").exists():
        sys.path.insert(0, str(backend_dir))
    elif (repo_or_backend / "manage.py").exists():
        sys.path.insert(0, str(repo_or_backend))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

    import django

    django.setup()


@dataclass(frozen=True)
class PolicySpec:
    kind: str = "scripted"
    model_path: str | None = None

    @property
    def label(self) -> str:
        if self.kind == "model" and self.model_path:
            return f"model:{Path(self.model_path).name}"
        return self.kind

    @property
    def actor_kind(self) -> str:
        return "model_ai" if self.kind == "model" else "scripted_ai"


@dataclass
class SelfPlayGameResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    winner: str = "none"
    decisions: int = 0
    terminal_reason: str = ""
    game_id: int | None = None


class LinearModelPolicyAdapter:
    def __init__(self, model_path: str):
        from ai.models.linear_policy import LinearPolicyModel

        self.model = LinearPolicyModel.load(model_path)

    def select_command_for_side(
        self,
        state,
        side: str,
        legal_commands,
        budget_ms: int = 100,
    ):
        from apps.gameplay.agents.observation import make_observation

        observation = make_observation(state, side).model_dump(mode="json")
        selected = self.model.select_command(observation, side, legal_commands)
        if selected is None:
            return None

        selected_key = command_key(selected)
        for legal_command in legal_commands:
            if command_key(legal_command) == selected_key:
                return legal_command
        return selected


def build_policy(spec: PolicySpec, deck):
    from apps.builder.schemas import DeckScript
    from apps.gameplay.agents.policies.random import RandomLegalPolicy
    from apps.gameplay.agents.policies.scripted import ScriptedPolicy

    if spec.kind == "scripted":
        return ScriptedPolicy(DeckScript.model_validate(deck.script or {}))
    if spec.kind == "random":
        return RandomLegalPolicy()
    if spec.kind == "model":
        if not spec.model_path:
            raise ValueError("Model policy requires model_path.")
        return LinearModelPolicyAdapter(spec.model_path)
    raise ValueError(f"Unknown policy kind: {spec.kind}")


def decision_side(state) -> str:
    if state.phase == "mulligan":
        for side in ("side_a", "side_b"):
            if not state.mulligan_done.get(side, False):
                return side
    return state.active


def select_command_for_side(policy, state, side: str, legal_commands):
    if hasattr(policy, "select_command_for_side"):
        return policy.select_command_for_side(state, side, legal_commands)
    return policy.select_command(state, legal_commands)


def ensure_no_active_game(deck_a, deck_b) -> None:
    from django.db.models import Q

    from apps.gameplay.models import Game

    existing_game = (
        Game.objects.filter(
            Q(side_a=deck_a, side_b=deck_b) | Q(side_a=deck_b, side_b=deck_a)
        )
        .exclude(status__in=[Game.GAME_STATUS_ENDED, Game.GAME_STATUS_ABORTED])
        .first()
    )
    if existing_game:
        raise ValueError(
            "An active Game already exists for these deck ids "
            f"(game_id={existing_game.id}). Use dedicated self-play decks or "
            "finish/delete that game first."
        )


def _decision_row(
    *,
    game,
    game_index: int,
    decision_index: int,
    state,
    side: str,
    policy_spec: PolicySpec,
    legal_commands: list[Any],
    command: Any,
    result,
) -> dict[str, Any]:
    from apps.gameplay.agents.hash import state_hash
    from apps.gameplay.agents.observation import make_observation

    errors = [
        error.model_dump(mode="json") if hasattr(error, "model_dump") else error
        for error in result.errors
    ]
    return {
        "source": "selfplay",
        "schema_version": 1,
        "game_index": game_index,
        "decision_index": decision_index,
        "game_id": game.id,
        "title_slug": game.title.slug,
        "ruleset_id": game.ruleset_id,
        "deck_ids": {
            "side_a": game.side_a_id,
            "side_b": game.side_b_id,
        },
        "actor_side": side,
        "actor_kind": policy_spec.actor_kind,
        "policy": policy_spec.label,
        "turn": state.turn,
        "phase": state.phase,
        "command": to_command_dict(command),
        "legal_commands": [to_command_dict(item) for item in legal_commands],
        "observation": make_observation(state, side).model_dump(mode="json"),
        "pre_state_hash": state_hash(state),
        "post_state_hash": result.post_state_hash,
        "outcome": "rejected" if errors else "accepted",
        "error": {"errors": errors} if errors else {},
        "final_winner": "",
    }


def run_selfplay_game(
    *,
    deck_a,
    deck_b,
    policy_a: PolicySpec,
    policy_b: PolicySpec,
    game_index: int = 1,
    max_decisions: int = 300,
    randomize_starting_player: bool = True,
    keep_game: bool = False,
) -> SelfPlayGameResult:
    from apps.gameplay.agents.legal import list_legal_commands
    from apps.gameplay.agents.simulator import apply_command, apply_effects
    from apps.gameplay.schemas.effects import StartGameEffect
    from apps.gameplay.services import GameService

    ensure_no_active_game(deck_a, deck_b)

    game = GameService.create_game(
        deck_a,
        deck_b,
        randomize_starting_player=randomize_starting_player,
    )
    rows: list[dict[str, Any]] = []
    terminal_reason = ""

    try:
        state = game.game_state
        state.ai_sides = []
        start_result = apply_effects(state, [StartGameEffect(side="side_a")])
        state = start_result.state
        if start_result.errors:
            terminal_reason = "start_errors"

        policies = {
            "side_a": build_policy(policy_a, game.side_a),
            "side_b": build_policy(policy_b, game.side_b),
        }
        specs = {
            "side_a": policy_a,
            "side_b": policy_b,
        }

        decisions = 0
        while (
            not terminal_reason and state.winner == "none" and decisions < max_decisions
        ):
            side = decision_side(state)
            legal_commands = list_legal_commands(state, side)
            if not legal_commands:
                terminal_reason = "no_legal_commands"
                break

            command = select_command_for_side(
                policies[side],
                state,
                side,
                legal_commands,
            )
            if command is None:
                terminal_reason = "policy_returned_none"
                break

            result = apply_command(state, side, command)
            rows.append(
                _decision_row(
                    game=game,
                    game_index=game_index,
                    decision_index=decisions + 1,
                    state=state,
                    side=side,
                    policy_spec=specs[side],
                    legal_commands=legal_commands,
                    command=command,
                    result=result,
                )
            )
            decisions += 1
            state = result.state
            if result.errors:
                terminal_reason = "command_errors"
                break

        if not terminal_reason:
            terminal_reason = "winner" if state.winner != "none" else "max_decisions"

        for row in rows:
            row["final_winner"] = state.winner
            row["terminal_reason"] = terminal_reason

        return SelfPlayGameResult(
            rows=rows,
            winner=state.winner,
            decisions=decisions,
            terminal_reason=terminal_reason,
            game_id=game.id,
        )
    finally:
        if not keep_game:
            game.delete()

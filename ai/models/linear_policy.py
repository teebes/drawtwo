from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ai.archetype.features import FEATURE_VERSION, command_features
from ai.data.replays import ReplayDecision, command_key, find_matching_command_index

MODEL_VERSION = "linear_command_ranker_v1"


@dataclass
class TrainingStats:
    rows_seen: int = 0
    rows_used: int = 0
    rows_skipped: int = 0
    updates: int = 0
    final_accuracy: float = 0.0


@dataclass
class LinearPolicyModel:
    weights: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def score_command(
        self,
        observation: dict[str, Any],
        actor_side: str,
        command: Any,
        *,
        row: dict[str, Any] | None = None,
        legal_commands: list[Any] | None = None,
    ) -> float:
        features = command_features(
            observation,
            actor_side,
            command,
            row=row,
            legal_commands=legal_commands,
        )
        return sum(
            self.weights.get(name, 0.0) * value for name, value in features.items()
        )

    def select_command(
        self,
        observation: dict[str, Any],
        actor_side: str,
        legal_commands: list[Any],
        *,
        row: dict[str, Any] | None = None,
    ) -> Any | None:
        if not legal_commands:
            return None

        scored = [
            (
                self.score_command(
                    observation,
                    actor_side,
                    command,
                    row=row,
                    legal_commands=legal_commands,
                ),
                command_key(command),
                index,
                command,
            )
            for index, command in enumerate(legal_commands)
        ]
        scored.sort(key=lambda item: (-item[0], item[1], item[2]))
        return scored[0][3]

    def save(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model_version": MODEL_VERSION,
            "feature_version": FEATURE_VERSION,
            "metadata": self.metadata,
            "weights": dict(sorted(self.weights.items())),
        }
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), "utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "LinearPolicyModel":
        payload = json.loads(Path(path).read_text("utf-8"))
        if payload.get("model_version") != MODEL_VERSION:
            raise ValueError(
                f"Unsupported model version: {payload.get('model_version')!r}"
            )
        if payload.get("feature_version") != FEATURE_VERSION:
            raise ValueError(
                f"Unsupported feature version: {payload.get('feature_version')!r}"
            )
        return cls(
            weights={
                str(key): float(value) for key, value in payload["weights"].items()
            },
            metadata=dict(payload.get("metadata") or {}),
        )


def _features_for(
    decision: ReplayDecision,
    command: Any,
) -> dict[str, float]:
    return command_features(
        decision.observation,
        decision.actor_side,
        command,
        row=decision.row,
        legal_commands=decision.legal_commands,
    )


def _score_features(
    weights: dict[str, float],
    features: dict[str, float],
) -> float:
    return sum(weights.get(name, 0.0) * value for name, value in features.items())


def _predict_index(
    weights: dict[str, float],
    decision: ReplayDecision,
) -> int | None:
    legal_commands = decision.legal_commands
    if not legal_commands:
        return None
    scored = []
    for index, command in enumerate(legal_commands):
        features = _features_for(decision, command)
        scored.append(
            (
                _score_features(weights, features),
                command_key(command),
                index,
            )
        )
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return scored[0][2]


def evaluate_accuracy(
    model: LinearPolicyModel,
    decisions: Iterable[ReplayDecision],
) -> tuple[int, int, float]:
    total = 0
    correct = 0
    for decision in decisions:
        target_index = find_matching_command_index(
            decision.command,
            decision.legal_commands,
        )
        if target_index is None:
            continue
        predicted_index = _predict_index(model.weights, decision)
        if predicted_index is None:
            continue
        total += 1
        if predicted_index == target_index:
            correct += 1
    accuracy = correct / total if total else 0.0
    return correct, total, accuracy


def train_linear_policy(
    decisions: list[ReplayDecision],
    *,
    epochs: int = 5,
    learning_rate: float = 0.1,
    shuffle: bool = True,
    seed: int = 0,
    metadata: dict[str, Any] | None = None,
) -> tuple[LinearPolicyModel, TrainingStats]:
    model = LinearPolicyModel(
        metadata={
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "epochs": epochs,
            "learning_rate": learning_rate,
            "rows_loaded": len(decisions),
            **(metadata or {}),
        }
    )
    stats = TrainingStats(rows_seen=len(decisions))
    rng = random.Random(seed)

    usable_decisions = [
        decision
        for decision in decisions
        if find_matching_command_index(decision.command, decision.legal_commands)
        is not None
    ]
    stats.rows_used = len(usable_decisions)
    stats.rows_skipped = len(decisions) - len(usable_decisions)

    for _epoch in range(epochs):
        epoch_decisions = list(usable_decisions)
        if shuffle:
            rng.shuffle(epoch_decisions)

        for decision in epoch_decisions:
            target_index = find_matching_command_index(
                decision.command,
                decision.legal_commands,
            )
            predicted_index = _predict_index(model.weights, decision)
            if target_index is None or predicted_index is None:
                continue
            if predicted_index == target_index:
                continue

            target_features = _features_for(
                decision,
                decision.legal_commands[target_index],
            )
            predicted_features = _features_for(
                decision,
                decision.legal_commands[predicted_index],
            )
            for name, value in target_features.items():
                model.weights[name] = (
                    model.weights.get(name, 0.0) + learning_rate * value
                )
            for name, value in predicted_features.items():
                model.weights[name] = (
                    model.weights.get(name, 0.0) - learning_rate * value
                )
            stats.updates += 1

    _correct, _total, stats.final_accuracy = evaluate_accuracy(model, usable_decisions)
    model.metadata.update(
        {
            "rows_used": stats.rows_used,
            "rows_skipped": stats.rows_skipped,
            "updates": stats.updates,
            "final_training_accuracy": stats.final_accuracy,
            "weight_count": len(model.weights),
        }
    )
    return model, stats

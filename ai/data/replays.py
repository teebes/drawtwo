from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


def to_command_dict(command: Any) -> dict[str, Any]:
    if hasattr(command, "model_dump"):
        return command.model_dump(mode="json")
    if isinstance(command, Mapping):
        return dict(command)
    raise TypeError(f"Unsupported command object: {type(command)!r}")


def _normalize_target_type(target_type: Any) -> Any:
    if target_type == "card":
        return "creature"
    return target_type


def normalize_command(command: Any) -> dict[str, Any]:
    raw = to_command_dict(command)
    command_type = raw.get("type")
    normalized: dict[str, Any] = {"type": command_type}

    if command_type == "cmd_play_card":
        normalized["card_id"] = str(raw.get("card_id", ""))
        normalized["position"] = int(raw.get("position", 0) or 0)
        if raw.get("target_id"):
            normalized["target_type"] = _normalize_target_type(raw.get("target_type"))
            normalized["target_id"] = str(raw.get("target_id", ""))
        return normalized

    if command_type == "cmd_attack":
        normalized["card_id"] = str(raw.get("card_id", ""))
        normalized["target_type"] = _normalize_target_type(raw.get("target_type"))
        normalized["target_id"] = str(raw.get("target_id", ""))
        return normalized

    if command_type == "cmd_use_hero":
        normalized["hero_id"] = str(raw.get("hero_id", ""))
        normalized["target_type"] = _normalize_target_type(raw.get("target_type"))
        normalized["target_id"] = str(raw.get("target_id", ""))
        return normalized

    if command_type == "cmd_mulligan":
        normalized["card_ids"] = sorted(
            str(card_id) for card_id in raw.get("card_ids", [])
        )
        return normalized

    return normalized


def command_key(command: Any) -> str:
    return json.dumps(
        normalize_command(command),
        sort_keys=True,
        separators=(",", ":"),
    )


def find_matching_command_index(
    command: Any,
    legal_commands: Iterable[Any],
) -> int | None:
    target_key = command_key(command)
    for index, legal_command in enumerate(legal_commands):
        if command_key(legal_command) == target_key:
            return index
    return None


@dataclass(frozen=True)
class ReplayDecision:
    row: dict[str, Any]
    source_path: str
    line_number: int

    @property
    def command(self) -> dict[str, Any]:
        return self.row.get("command") or {}

    @property
    def legal_commands(self) -> list[dict[str, Any]]:
        return list(self.row.get("legal_commands") or [])

    @property
    def observation(self) -> dict[str, Any]:
        return dict(self.row.get("observation") or {})

    @property
    def actor_side(self) -> str:
        return self.row.get("actor_side") or self.observation.get("side") or "side_a"


def iter_jsonl(path: str | Path) -> Iterable[tuple[int, dict[str, Any]]]:
    replay_path = Path(path)
    with replay_path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            yield line_number, json.loads(stripped)


def load_replay_decisions(
    paths: Iterable[str | Path],
    *,
    accepted_only: bool = True,
    actor_kind: str | None = None,
    title: str | None = None,
    limit: int | None = None,
) -> list[ReplayDecision]:
    return list(
        iter_replay_decisions(
            paths,
            accepted_only=accepted_only,
            actor_kind=actor_kind,
            title=title,
            limit=limit,
        )
    )


def iter_replay_decisions(
    paths: Iterable[str | Path],
    *,
    accepted_only: bool = True,
    actor_kind: str | None = None,
    title: str | None = None,
    limit: int | None = None,
) -> Iterable[ReplayDecision]:
    yielded = 0
    for path in paths:
        for line_number, row in iter_jsonl(path):
            if accepted_only and row.get("outcome", "accepted") != "accepted":
                continue
            if actor_kind and row.get("actor_kind") != actor_kind:
                continue
            if title and row.get("title_slug") != title:
                continue

            decision = ReplayDecision(
                row=row,
                source_path=str(path),
                line_number=line_number,
            )
            if not decision.command or not decision.legal_commands:
                continue

            yield decision
            yielded += 1
            if limit is not None and yielded >= limit:
                return

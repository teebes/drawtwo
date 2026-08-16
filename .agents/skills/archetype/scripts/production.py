#!/usr/bin/env python3
"""Guarded production inventory and manifest operations for Archetype."""

from __future__ import annotations

import argparse
import base64
import difflib
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

TITLE_SLUG = "archetype"
SSH_OPTIONS = (
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=10",
    "-o",
    "ConnectionAttempts=1",
    "-o",
    "ServerAliveInterval=15",
    "-o",
    "ServerAliveCountMax=2",
)
REMOTE_TIMEOUT_SECONDS = 120
PRODUCTION_CONFIG_ENV = "DRAWTWO_PROD_CONFIG"
PRODUCTION_FIELD_ENVS = {
    "ssh_host": "DRAWTWO_PROD_SSH_HOST",
    "workdir": "DRAWTWO_PROD_WORKDIR",
    "compose_file": "DRAWTWO_PROD_COMPOSE_FILE",
    "env_file": "DRAWTWO_PROD_ENV_FILE",
    "backend_service": "DRAWTWO_PROD_BACKEND_SERVICE",
}
SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = SKILL_ROOT / "references" / "production-snapshot.yaml"
DEFAULT_METADATA = SKILL_ROOT / "references" / "production-snapshot.meta.json"
TOP_LEVEL_RESOURCE = re.compile(r"(?m)(?=^- type: )")


class ProductionError(RuntimeError):
    """A guarded production operation failed."""


def _production_settings() -> dict[str, str]:
    settings: dict[str, str] = {}
    config_value = os.environ.get(PRODUCTION_CONFIG_ENV)
    if config_value:
        config_path = Path(config_value).expanduser()
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProductionError(
                f"Cannot load private production config {config_path}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise ProductionError("Private production config must be a JSON object.")
        configured = payload.get("production", payload)
        if not isinstance(configured, dict):
            raise ProductionError(
                "The production entry in the private config must be a JSON object."
            )
        settings.update(
            {
                field: value
                for field, value in configured.items()
                if field in PRODUCTION_FIELD_ENVS and isinstance(value, str)
            }
        )

    for field, env_name in PRODUCTION_FIELD_ENVS.items():
        value = os.environ.get(env_name)
        if value:
            settings[field] = value

    missing = [field for field in PRODUCTION_FIELD_ENVS if not settings.get(field)]
    if missing:
        raise ProductionError(
            "Production coordinates are not configured. Set "
            f"{PRODUCTION_CONFIG_ENV} to a private JSON file or provide: "
            + ", ".join(PRODUCTION_FIELD_ENVS[field] for field in missing)
        )

    for field, value in settings.items():
        if any(character in value for character in ("\0", "\n", "\r")):
            raise ProductionError(
                "Private production config field "
                f"{field!r} contains a control character."
            )
    if not Path(settings["workdir"]).is_absolute():
        raise ProductionError("Private production workdir must be an absolute path.")
    if settings["ssh_host"].startswith("-"):
        raise ProductionError("Private production SSH destination is invalid.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", settings["backend_service"]):
        raise ProductionError("Private production backend service name is invalid.")
    return settings


def _run_remote(source: str) -> str:
    settings = _production_settings()
    compose_command = shlex.join(
        [
            "docker",
            "compose",
            "-f",
            settings["compose_file"],
            "--env-file",
            settings["env_file"],
            "exec",
            "-T",
            settings["backend_service"],
            "python",
            "manage.py",
            "shell",
        ]
    )
    remote_command = f"cd {shlex.quote(settings['workdir'])} && {compose_command}"
    try:
        completed = subprocess.run(
            ["ssh", "-T", *SSH_OPTIONS, settings["ssh_host"], remote_command],
            input=source,
            text=True,
            capture_output=True,
            check=False,
            timeout=REMOTE_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise ProductionError("The ssh executable is not available.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ProductionError(
            f"Production command exceeded {REMOTE_TIMEOUT_SECONDS} seconds."
        ) from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ProductionError(
            f"Production command failed with exit code {completed.returncode}: {detail}"
        )
    return completed.stdout


def _capture() -> dict:
    source = textwrap.dedent(
        f"""
        import hashlib
        import json
        import yaml
        from django.db import connection, transaction
        from django.utils import timezone
        from apps.builder.models import Title
        from apps.builder.services import TitleService

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                cursor.execute("SET TRANSACTION READ ONLY")
            title = Title.objects.get(slug={TITLE_SLUG!r}, is_latest=True)
            assert title.status == Title.STATUS_PUBLISHED, title.status
            snapshot = TitleService(title).export_snapshot_yaml()
            resources = yaml.safe_load(snapshot)

        metadata = {{
            "schema_version": 1,
            "environment": "production",
            "title_slug": title.slug,
            "title_id": title.id,
            "title_version": title.version,
            "title_status": title.status,
            "captured_at": timezone.now().isoformat(),
            "sha256": hashlib.sha256(snapshot.encode("utf-8")).hexdigest(),
            "cards": sum(item.get("type") == "card" for item in resources),
            "heroes": sum(item.get("type") == "hero" for item in resources),
        }}
        print(json.dumps({{"metadata": metadata, "snapshot": snapshot}}))
        """
    )
    try:
        payload = json.loads(_run_remote(source))
    except json.JSONDecodeError as exc:
        raise ProductionError(
            "Production returned an invalid inventory payload."
        ) from exc

    snapshot = payload.get("snapshot")
    metadata = payload.get("metadata")
    if not isinstance(snapshot, str) or not isinstance(metadata, dict):
        raise ProductionError("Production inventory payload is missing snapshot data.")
    if not snapshot.startswith("- type: title\n  slug: archetype\n"):
        raise ProductionError(
            "Production snapshot did not identify the Archetype title."
        )
    digest = hashlib.sha256(snapshot.encode("utf-8")).hexdigest()
    if digest != metadata.get("sha256"):
        raise ProductionError("Production snapshot checksum did not verify.")
    if not metadata.get("cards") or not metadata.get("heroes"):
        raise ProductionError(
            "Production snapshot unexpectedly has no cards or heroes."
        )
    return payload


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", text=True
    )
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _write_or_print(content: str, output: Path | None) -> None:
    if output is None:
        print(content, end="" if content.endswith("\n") else "\n")
    else:
        _atomic_write(output, content)


def _blocks(snapshot: str) -> list[str]:
    stripped = snapshot.strip()
    if not stripped:
        return []
    if re.match(r"^type:\s", stripped):
        lines = stripped.splitlines()
        normalized = f"- {lines[0]}\n"
        if len(lines) > 1:
            normalized += textwrap.indent("\n".join(lines[1:]), "  ") + "\n"
        return [normalized]
    return [part for part in TOP_LEVEL_RESOURCE.split(snapshot) if part.strip()]


def _scalar(block: str, field: str) -> str | None:
    match = re.search(rf"(?m)^  {re.escape(field)}: (.*)$", block)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value


def _identity(block: str) -> tuple[str, str]:
    resource_type = _scalar(block, "type")
    if resource_type is None:
        match = re.match(r"^- type: ([^\n]+)", block)
        resource_type = match.group(1).strip() if match else None
    if not resource_type:
        raise ProductionError("A manifest resource is missing type.")
    slug = _scalar(block, "slug")
    if resource_type == "config":
        slug = TITLE_SLUG
    if not slug:
        raise ProductionError(f"The {resource_type} resource is missing slug.")
    return resource_type, slug


def _resource_map(snapshot: str) -> dict[tuple[str, str], str]:
    resources: dict[tuple[str, str], str] = {}
    for block in _blocks(snapshot):
        identity = _identity(block)
        if identity in resources:
            raise ProductionError(f"Duplicate resource in YAML: {identity}")
        resources[identity] = block
    return resources


def command_refresh(args: argparse.Namespace) -> None:
    payload = _capture()
    snapshot_path = args.snapshot.resolve()
    metadata_path = args.metadata.resolve()
    _atomic_write(snapshot_path, payload["snapshot"])
    _atomic_write(
        metadata_path,
        json.dumps(payload["metadata"], indent=2, sort_keys=True) + "\n",
    )
    print(
        json.dumps(
            {
                "snapshot": str(snapshot_path),
                "metadata": str(metadata_path),
                **payload["metadata"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def command_export(args: argparse.Namespace) -> None:
    _write_or_print(_capture()["snapshot"], args.output)


def command_extract(args: argparse.Namespace) -> None:
    snapshot = args.snapshot.read_text(encoding="utf-8")
    candidates = []
    for block in _blocks(snapshot):
        resource_type, slug = _identity(block)
        if resource_type != args.kind:
            continue
        name = _scalar(block, "name") or ""
        candidates.append((slug, name, block))

    slug_matches = [entry for entry in candidates if entry[0] == args.selector]
    matches = slug_matches or [
        entry for entry in candidates if entry[1].casefold() == args.selector.casefold()
    ]
    if len(matches) != 1:
        options = ", ".join(f"{slug} ({name})" for slug, name, _ in candidates)
        raise ProductionError(
            f"Expected one {args.kind} matching {args.selector!r}; found "
            f"{len(matches)}. Available: {options}"
        )
    _write_or_print(matches[0][2], args.output)


def command_diff(args: argparse.Namespace) -> None:
    baseline = _resource_map(args.snapshot.read_text(encoding="utf-8"))
    changes = _resource_map(args.manifest.read_text(encoding="utf-8"))
    output: list[str] = []
    for identity, after in changes.items():
        before = baseline.get(identity, "")
        resource_type, slug = identity
        output.extend(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"production/{resource_type}/{slug}",
                tofile=f"proposed/{resource_type}/{slug}",
            )
        )
    if not output:
        print("No changes.")
    else:
        print("".join(output), end="" if output[-1].endswith("\n") else "\n")


def _manifest_source(
    manifest: str,
    *,
    allow_create: bool,
    allow_shape_change: bool,
    allow_bulk: bool,
    apply: bool,
    expected_sha256: str | None = None,
) -> str:
    encoded = base64.b64encode(manifest.encode("utf-8")).decode("ascii")
    expected = repr(expected_sha256) if expected_sha256 else "None"
    return textwrap.dedent(
        f"""
        import base64
        from contextlib import nullcontext
        import hashlib
        import json
        import yaml
        from django.db import connection, transaction
        from apps.builder.models import (
            CardTemplate,
            Faction,
            HeroTemplate,
            Tag,
            Title,
            TraitOverride,
        )
        from apps.builder.services import TitleService
        from apps.builder.trait_definitions import validate_trait_slug

        def resource_identity(item):
            resource_type = item.get("type")
            if resource_type == "config":
                return ("config", {TITLE_SLUG!r})
            return (resource_type, item.get("slug", {TITLE_SLUG!r}))

        def extra_paths(raw_value, canonical_value, path=""):
            paths = []
            if isinstance(raw_value, dict) and isinstance(canonical_value, dict):
                for key in sorted(set(raw_value) - set(canonical_value)):
                    paths.append(f"{{path}}.{{key}}" if path else key)
                for key in set(raw_value) & set(canonical_value):
                    child_path = f"{{path}}.{{key}}" if path else key
                    paths.extend(
                        extra_paths(raw_value[key], canonical_value[key], child_path)
                    )
            elif isinstance(raw_value, list) and isinstance(canonical_value, list):
                for index, (raw_item, canonical_item) in enumerate(
                    zip(raw_value, canonical_value)
                ):
                    paths.extend(
                        extra_paths(
                            raw_item,
                            canonical_item,
                            f"{{path}}[{{index}}]",
                        )
                    )
            return paths

        def missing_paths(expected_value, raw_value, path=""):
            paths = []
            if isinstance(expected_value, dict) and isinstance(raw_value, dict):
                for key in sorted(set(expected_value) - set(raw_value)):
                    paths.append(f"{{path}}.{{key}}" if path else key)
                for key in set(expected_value) & set(raw_value):
                    child_path = f"{{path}}.{{key}}" if path else key
                    paths.extend(
                        missing_paths(expected_value[key], raw_value[key], child_path)
                    )
            elif isinstance(expected_value, list) and isinstance(raw_value, list):
                for index, (expected_item, raw_item) in enumerate(
                    zip(expected_value, raw_value)
                ):
                    paths.extend(
                        missing_paths(
                            expected_item,
                            raw_item,
                            f"{{path}}[{{index}}]",
                        )
                    )
            return paths

        def discriminator_identity(value):
            if not isinstance(value, dict):
                return ()
            return tuple(
                (key, value.get(key))
                for key in ("type", "action", "card_type")
                if key in value
            )

        def missing_live_paths(current_value, proposed_value, path=""):
            paths = []
            if isinstance(current_value, dict) and isinstance(proposed_value, dict):
                for key in sorted(set(current_value) - set(proposed_value)):
                    paths.append(f"{{path}}.{{key}}" if path else key)
                for key in set(current_value) & set(proposed_value):
                    child_path = f"{{path}}.{{key}}" if path else key
                    paths.extend(
                        missing_live_paths(
                            current_value[key], proposed_value[key], child_path
                        )
                    )
            elif isinstance(current_value, list) and isinstance(proposed_value, list):
                pairs = list(zip(current_value, proposed_value))
                if (
                    current_value
                    and proposed_value
                    and max(len(current_value), len(proposed_value)) <= 10
                ):
                    current_signatures = [
                        structural_signature(item) for item in current_value
                    ]
                    proposed_signatures = [
                        structural_signature(item) for item in proposed_value
                    ]
                    mismatch_penalty = 1_000_000
                    if len(current_value) <= len(proposed_value):
                        costs = [
                            [
                                value_distance(current_item, proposed_item)
                                + (
                                    0
                                    if current_signatures[current_index]
                                    == proposed_signatures[proposed_index]
                                    else mismatch_penalty
                                )
                                for proposed_index, proposed_item in enumerate(
                                    proposed_value
                                )
                            ]
                            for current_index, current_item in enumerate(current_value)
                        ]
                        _, assignment = minimum_assignment(costs)
                        pairs = [
                            (current_value[index], proposed_value[column])
                            for index, column in enumerate(assignment)
                        ]
                    else:
                        costs = [
                            [
                                value_distance(current_item, proposed_item)
                                + (
                                    0
                                    if current_signatures[current_index]
                                    == proposed_signatures[proposed_index]
                                    else mismatch_penalty
                                )
                                for current_index, current_item in enumerate(
                                    current_value
                                )
                            ]
                            for proposed_index, proposed_item in enumerate(
                                proposed_value
                            )
                        ]
                        _, assignment = minimum_assignment(costs)
                        pairs = [
                            (current_value[column], proposed_value[index])
                            for index, column in enumerate(assignment)
                        ]
                for index, (current_item, proposed_item) in enumerate(pairs):
                    current_identity = discriminator_identity(current_item)
                    proposed_identity = discriminator_identity(proposed_item)
                    if (
                        current_identity
                        and proposed_identity
                        and current_identity != proposed_identity
                    ):
                        continue
                    paths.extend(
                        missing_live_paths(
                            current_item,
                            proposed_item,
                            f"{{path}}[{{index}}]",
                        )
                    )
            return paths

        def structural_signature(value):
            if isinstance(value, dict):
                discriminators = tuple(
                    (key, value.get(key))
                    for key in ("type", "action", "card_type")
                    if key in value
                )
                nested = tuple(
                    (key, structural_signature(child))
                    for key, child in sorted(value.items())
                    if isinstance(child, (dict, list))
                )
                return ("dict", tuple(sorted(value)), discriminators, nested)
            if isinstance(value, list):
                if all(not isinstance(item, (dict, list)) for item in value):
                    return ("scalar-list", tuple(value))
                return (
                    "list",
                    tuple(structural_signature(item) for item in value),
                )
            return ("scalar", type(value).__name__)

        def value_distance(left, right):
            if isinstance(left, dict) and isinstance(right, dict):
                shared = set(left) & set(right)
                return len(set(left) ^ set(right)) + sum(
                    value_distance(left[key], right[key]) for key in shared
                )
            if isinstance(left, list) and isinstance(right, list):
                return abs(len(left) - len(right)) + sum(
                    value_distance(left_item, right_item)
                    for left_item, right_item in zip(left, right)
                )
            return int(left != right)

        def minimum_assignment(costs):
            if not costs:
                return (0, ())
            states = {{0: (0, ())}}
            for row in costs:
                next_states = {{}}
                for used, (total, assignment) in states.items():
                    for column, cost in enumerate(row):
                        bit = 1 << column
                        if used & bit:
                            continue
                        candidate = (total + cost, assignment + (column,))
                        key = used | bit
                        if key not in next_states or candidate < next_states[key]:
                            next_states[key] = candidate
                states = next_states
            return min(states.values())

        def looks_reordered(current_value, proposed_value, signatures):
            groups = {{}}
            for index, signature in enumerate(signatures):
                groups.setdefault(signature, []).append(index)
            for indices in groups.values():
                if len(indices) < 2:
                    continue
                if len(indices) > 10:
                    if any(
                        current_value[index] != proposed_value[index]
                        for index in indices
                    ):
                        return True
                    continue
                costs = [
                    [
                        value_distance(
                            current_value[current_index],
                            proposed_value[proposed_index],
                        )
                        for proposed_index in indices
                    ]
                    for current_index in indices
                ]
                identity_cost = sum(
                    costs[index][index] for index in range(len(indices))
                )
                best_cost, _ = minimum_assignment(costs)
                if best_cost < identity_cost:
                    return True
            return False

        def shape_change_paths(current_value, proposed_value, path=""):
            paths = []
            if proposed_value is None:
                if current_value is not None:
                    paths.append(path or "<resource>")
            elif isinstance(current_value, dict) and isinstance(
                proposed_value, dict
            ):
                current_keys = set(current_value)
                proposed_keys = set(proposed_value)
                for key in sorted(current_keys ^ proposed_keys):
                    paths.append(f"{{path}}.{{key}}" if path else key)
                for discriminator in ("type", "action", "card_type"):
                    if (
                        discriminator in current_value
                        and discriminator in proposed_value
                        and current_value[discriminator]
                        != proposed_value[discriminator]
                    ):
                        paths.append(
                            f"{{path}}.{{discriminator}}"
                            if path
                            else discriminator
                        )
                for key in current_keys & proposed_keys:
                    child_path = f"{{path}}.{{key}}" if path else key
                    paths.extend(
                        shape_change_paths(
                            current_value[key],
                            proposed_value[key],
                            child_path,
                        )
                    )
            elif isinstance(current_value, list) and isinstance(proposed_value, list):
                if len(proposed_value) != len(current_value):
                    paths.append(f"{{path}}.length")
                scalar_list = all(
                    not isinstance(item, (dict, list))
                    for item in [*current_value, *proposed_value]
                )
                if scalar_list:
                    if current_value != proposed_value:
                        paths.append(path)
                else:
                    current_signatures = [
                        structural_signature(item) for item in current_value
                    ]
                    proposed_signatures = [
                        structural_signature(item) for item in proposed_value
                    ]
                    if current_signatures != proposed_signatures:
                        paths.append(path)
                    elif looks_reordered(
                        current_value, proposed_value, current_signatures
                    ):
                        paths.append(path)
                    for index, (current_item, proposed_item) in enumerate(
                        zip(current_value, proposed_value)
                    ):
                        paths.extend(
                            shape_change_paths(
                                current_item,
                                proposed_item,
                                f"{{path}}[{{index}}]",
                            )
                        )
            elif isinstance(current_value, (dict, list)) or isinstance(
                proposed_value, (dict, list)
            ):
                paths.append(path or "<resource>")
            return paths

        def summon_targets(value):
            targets = []
            if isinstance(value, dict):
                if value.get("action") == "summon" and isinstance(
                    value.get("target"), str
                ):
                    targets.append(value["target"])
                for child in value.values():
                    targets.extend(summon_targets(child))
            elif isinstance(value, list):
                for child in value:
                    targets.extend(summon_targets(child))
            return targets

        manifest = base64.b64decode({encoded!r}).decode("utf-8")
        raw = yaml.safe_load(manifest)
        raw_resources = raw if isinstance(raw, list) else [raw]
        if not raw_resources or not all(
            isinstance(item, dict) for item in raw_resources
        ):
            raise ValueError("Manifest must contain one or more resource objects.")
        if {apply!r} and len(raw_resources) > 1 and not {allow_bulk!r}:
            raise ValueError(
                "A production apply may contain only one resource unless "
                "--confirm-bulk-production archetype is provided."
            )

        allowed_types = {{
            "title", "config", "faction", "tag", "trait_override", "hero", "card"
        }}
        complete_fields = {{
            "title": {{"type", "slug", "name", "description"}},
            "config": {{
                "type", "deck_size_limit", "min_cards_in_deck",
                "deck_card_max_count", "hand_start_size", "death_retaliation",
                "ranked_time_per_turn",
            }},
            "faction": {{"type", "slug", "name", "description"}},
            "tag": {{"type", "slug", "name", "description"}},
            "trait_override": {{"type", "slug", "name", "description"}},
            "card": {{
                "type", "card_type", "slug", "name", "description", "cost",
                "attack", "health", "traits", "spec", "tags", "is_collectible",
                "hero_slugs",
            }},
            "hero": {{
                "type", "slug", "name", "description", "health", "hero_power", "spec"
            }},
        }}
        identities = set()
        for item in raw_resources:
            resource_type = item.get("type")
            if resource_type not in allowed_types:
                raise ValueError(
                    f"Unsupported production resource type: {{resource_type!r}}"
                )
            missing = complete_fields.get(resource_type, set()) - set(item)
            if missing:
                raise ValueError(
                    f"{{resource_type}} {{item.get('slug')!r}} is not a complete "
                    f"exported resource; missing {{sorted(missing)}}"
                )
            if resource_type == "card" and set(item) & {{"id", "art_url"}}:
                raise ValueError(
                    "Card manifests must not contain id or art_url; neither is a "
                    "portable persisted content field."
                )
            if resource_type == "hero":
                hero_power = item.get("hero_power")
                if not isinstance(hero_power, dict):
                    raise ValueError("hero_power must be an object.")
                missing_power_fields = {{"name", "cost", "actions"}} - set(
                    hero_power
                )
                if missing_power_fields:
                    raise ValueError(
                        "hero_power is incomplete; missing "
                        f"{{sorted(missing_power_fields)}}"
                    )
            identity = resource_identity(item)
            if identity in identities:
                raise ValueError(f"Duplicate resource: {{identity}}")
            identities.add(identity)

        write_context = transaction.atomic() if {apply!r} else nullcontext()
        with write_context:
            if {apply!r}:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
                    )
            titles = Title.objects.select_for_update() if {apply!r} else Title.objects
            title = titles.get(slug={TITLE_SLUG!r}, is_latest=True)
            if title.status != Title.STATUS_PUBLISHED:
                raise ValueError(f"Archetype is not published: {{title.status}}")

            if {apply!r}:
                lock_queries = (
                    CardTemplate.objects.filter(title=title, is_latest=True),
                    HeroTemplate.objects.filter(title=title, is_latest=True),
                    Faction.objects.filter(title=title),
                    Tag.objects.filter(title=title),
                    TraitOverride.objects.filter(title=title),
                )
                for query in lock_queries:
                    list(query.select_for_update().values_list("pk", flat=True))

            service = TitleService(title)
            before = service.export_snapshot_yaml()
            actual_sha256 = hashlib.sha256(before.encode("utf-8")).hexdigest()
            expected_sha256 = {expected}
            if expected_sha256 and actual_sha256 != expected_sha256:
                raise ValueError(
                    "Production changed after the baseline was captured; refresh and "
                    "rebuild the manifest. "
                    f"expected={{expected_sha256}} actual={{actual_sha256}}"
                )

            resources = service.parse_yaml_resources(manifest)
            canonical_resources = []
            for raw_item, resource in zip(raw_resources, resources):
                canonical = resource.model_dump(
                    exclude_none=False, exclude_defaults=False
                )
                canonical_resources.append(canonical)
                extras = extra_paths(raw_item, canonical)
                if extras:
                    raise ValueError(
                        f"{{resource_identity(raw_item)}} contains unknown fields: "
                        f"{{extras}}"
                    )
                exported = resource.model_dump(
                    exclude_none=True, exclude_defaults=False
                )
                missing = missing_paths(exported, raw_item)
                if missing:
                    raise ValueError(
                        f"{{resource_identity(raw_item)}} is not a complete "
                        f"exported resource; missing fields: {{missing}}"
                    )

            current_resources = yaml.safe_load(before)
            current_by_identity = {{
                resource_identity(item): item
                for item in current_resources
            }}
            for item in raw_resources:
                identity = resource_identity(item)
                current_item = current_by_identity.get(identity)
                if current_item:
                    missing_top_level = set(current_item) - set(item)
                    if missing_top_level:
                        raise ValueError(
                            f"{{identity}} omits fields present on the live resource: "
                            f"{{sorted(missing_top_level)}}. Copy the complete live "
                            "resource and use an explicit null to clear an optional "
                            "field."
                        )
                    missing_live = missing_live_paths(current_item, item)
                    if missing_live:
                        raise ValueError(
                            f"{{identity}} omits fields from unchanged live "
                            f"structures: {{sorted(set(missing_live))}}. Copy the "
                            "complete live resource and use an explicit null to "
                            "clear an optional field."
                        )
                    if not {allow_shape_change!r}:
                        shape_changes = shape_change_paths(current_item, item)
                        if shape_changes:
                            raise ValueError(
                                f"{{identity}} changes live structure: "
                                f"{{sorted(set(shape_changes))}}. Use "
                                "--allow-shape-change only for an explicitly "
                                "requested structural edit."
                            )

            manifest_slugs = {{
                resource_type: {{
                    resource.slug
                    for resource in resources
                    if resource.type == resource_type
                }}
                for resource_type in (
                    "card", "faction", "hero", "tag", "trait_override"
                )
            }}
            available_card_types = dict(
                CardTemplate.objects.filter(
                    title=title, is_latest=True
                ).values_list("slug", "card_type")
            )
            available_card_types.update({{
                resource.slug: resource.card_type
                for resource in resources
                if resource.type == "card"
            }})
            available_cards = set(available_card_types)
            post_change_by_identity = dict(current_by_identity)
            for raw_item, canonical in zip(raw_resources, canonical_resources):
                post_change_by_identity[resource_identity(raw_item)] = canonical
            available_factions = set(
                Faction.objects.filter(title=title).values_list("slug", flat=True)
            ) | manifest_slugs["faction"]
            available_heroes = set(
                HeroTemplate.objects.filter(
                    title=title, is_latest=True
                ).values_list("slug", flat=True)
            ) | manifest_slugs["hero"]
            available_tags = set(
                Tag.objects.filter(title=title).values_list("slug", flat=True)
            ) | manifest_slugs["tag"]

            for resource in resources:
                if resource.type == "title" and resource.slug != {TITLE_SLUG!r}:
                    raise ValueError("Title resource slug must be archetype.")
                faction = getattr(resource, "faction", None)
                if faction and faction not in available_factions:
                    raise ValueError(
                        f"{{resource.type}} {{resource.slug!r}} references missing "
                        f"faction {{faction!r}}."
                    )
                if resource.type == "card":
                    missing_tags = set(resource.tags) - available_tags
                    if missing_tags:
                        raise ValueError(
                            f"Card {{resource.slug!r}} references missing tags "
                            f"{{sorted(missing_tags)}}."
                        )
                    missing_heroes = set(resource.hero_slugs) - available_heroes
                    if missing_heroes:
                        raise ValueError(
                            f"Card {{resource.slug!r}} references missing heroes "
                            f"{{sorted(missing_heroes)}}."
                        )
                    exists = CardTemplate.objects.filter(
                        title=title, slug=resource.slug, is_latest=True
                    ).exists()
                    if not exists and not {allow_create!r}:
                        raise ValueError(
                            f"Card {{resource.slug!r}} does not exist. Refusing to "
                            "create it without --allow-create."
                        )
                if resource.type == "config":
                    if resource.deck_size_limit < 1:
                        raise ValueError("Deck size limit must be at least 1.")
                    if resource.min_cards_in_deck < 0:
                        raise ValueError("Minimum cards in deck cannot be negative.")
                    if resource.min_cards_in_deck > resource.deck_size_limit:
                        raise ValueError(
                            "Minimum cards in deck cannot exceed the deck size limit."
                        )
                    if resource.deck_card_max_count < 1:
                        raise ValueError(
                            "Maximum copies of a card must be at least 1."
                        )
                    if not 0 <= resource.hand_start_size <= resource.deck_size_limit:
                        raise ValueError(
                            "Starting hand size must be between 0 and deck size."
                        )
                    if resource.ranked_time_per_turn < 0:
                        raise ValueError(
                            "Ranked time per turn cannot be negative."
                        )
                    compensation = resource.side_b_compensation
                    if compensation and compensation not in available_cards:
                        raise ValueError(
                            "side_b_compensation references missing card "
                            f"{{compensation!r}}."
                        )
                if resource.type == "hero":
                    exists = HeroTemplate.objects.filter(
                        title=title, slug=resource.slug, is_latest=True
                    ).exists()
                    if not exists and not {allow_create!r}:
                        raise ValueError(
                            f"Hero {{resource.slug!r}} does not exist. Refusing to "
                            "create it without --allow-create."
                        )
                if resource.type == "trait_override" and not validate_trait_slug(
                    resource.slug
                ):
                    raise ValueError(
                        f"Unknown trait override slug: {{resource.slug!r}}"
                    )
                if resource.type in {{"faction", "tag", "trait_override"}}:
                    model = {{
                        "faction": Faction,
                        "tag": Tag,
                        "trait_override": TraitOverride,
                    }}[resource.type]
                    exists = model.objects.filter(
                        title=title, slug=resource.slug
                    ).exists()
                    if not exists and not {allow_create!r}:
                        raise ValueError(
                            f"{{resource.type.replace('_', ' ').title()}} "
                            f"{{resource.slug!r}} does not exist. Refusing to create "
                            "it without --allow-create."
                        )

            for identity, item in post_change_by_identity.items():
                summon_slugs = set(summon_targets(item))
                missing_summons = summon_slugs - available_cards
                if missing_summons:
                    raise ValueError(
                        f"{{identity}} "
                        f"summons missing cards {{sorted(missing_summons)}}."
                    )
                non_creature_summons = {{
                    slug
                    for slug in summon_slugs
                    if available_card_types.get(slug) != "creature"
                }} - missing_summons
                if non_creature_summons:
                    raise ValueError(
                        f"{{identity}} "
                        "summons non-creature cards "
                        f"{{sorted(non_creature_summons)}}."
                    )

            if {apply!r}:
                results = service.ingest_resources(resources)
                after = service.export_snapshot_yaml()
            else:
                results = []
                after = before

        print(json.dumps({{
            "validated": True,
            "applied": {apply!r},
            "resources": [
                {{
                    "type": resource.type,
                    "slug": getattr(resource, "slug", ""),
                    "name": getattr(resource, "name", ""),
                }}
                for resource in resources
            ],
            "results": [result.model_dump() for result in results],
            "before_sha256": actual_sha256,
            "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
        }}, indent=2, sort_keys=True))
        """
    )


def command_validate(args: argparse.Namespace) -> None:
    manifest = args.manifest.read_text(encoding="utf-8")
    result = _run_remote(
        _manifest_source(
            manifest,
            allow_create=args.allow_create,
            allow_shape_change=args.allow_shape_change,
            allow_bulk=True,
            apply=False,
        )
    )
    print(result, end="" if result.endswith("\n") else "\n")


def command_apply(args: argparse.Namespace) -> None:
    if args.confirm_production != TITLE_SLUG:
        raise ProductionError(
            f"Refusing production write: pass --confirm-production {TITLE_SLUG}"
        )
    if args.confirm_bulk_production not in (None, TITLE_SLUG):
        raise ProductionError(
            "Refusing bulk production write: pass "
            f"--confirm-bulk-production {TITLE_SLUG}"
        )
    manifest = args.manifest.read_text(encoding="utf-8")
    baseline = args.baseline.read_text(encoding="utf-8")
    expected_sha256 = hashlib.sha256(baseline.encode("utf-8")).hexdigest()
    result = _run_remote(
        _manifest_source(
            manifest,
            allow_create=args.allow_create,
            allow_shape_change=args.allow_shape_change,
            allow_bulk=args.confirm_bulk_production == TITLE_SLUG,
            apply=True,
            expected_sha256=expected_sha256,
        )
    )
    print(result, end="" if result.endswith("\n") else "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect and safely update production Archetype content."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    refresh = subparsers.add_parser(
        "refresh", help="Refresh the checked-in production snapshot and metadata."
    )
    refresh.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    refresh.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    refresh.set_defaults(func=command_refresh)

    export = subparsers.add_parser("export", help="Print the live snapshot.")
    export.add_argument("--output", "-o", type=Path)
    export.set_defaults(func=command_export)

    extract = subparsers.add_parser(
        "extract", help="Extract one complete card or hero resource from a snapshot."
    )
    extract.add_argument("kind", choices=("card", "hero"))
    extract.add_argument(
        "selector", help="Exact slug, then exact case-insensitive name."
    )
    extract.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    extract.add_argument("--output", "-o", type=Path)
    extract.set_defaults(func=command_extract)

    diff = subparsers.add_parser(
        "diff", help="Show resource-level differences from the production snapshot."
    )
    diff.add_argument("manifest", type=Path)
    diff.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    diff.set_defaults(func=command_diff)

    validate = subparsers.add_parser(
        "validate",
        help="Validate a complete manifest against production without writes.",
    )
    validate.add_argument("manifest", type=Path)
    validate.add_argument("--allow-create", action="store_true")
    validate.add_argument("--allow-shape-change", action="store_true")
    validate.set_defaults(func=command_validate)

    apply_parser = subparsers.add_parser(
        "apply", help="Apply a complete manifest to production with stale-state checks."
    )
    apply_parser.add_argument("manifest", type=Path)
    apply_parser.add_argument("--baseline", type=Path, default=DEFAULT_SNAPSHOT)
    apply_parser.add_argument("--allow-create", action="store_true")
    apply_parser.add_argument("--allow-shape-change", action="store_true")
    apply_parser.add_argument("--confirm-production", required=True)
    apply_parser.add_argument("--confirm-bulk-production")
    apply_parser.set_defaults(func=command_apply)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except (OSError, ProductionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

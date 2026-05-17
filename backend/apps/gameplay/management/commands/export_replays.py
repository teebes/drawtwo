import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.gameplay.models import GameAction


class Command(BaseCommand):
    help = "Export command-level game action logs for AI training datasets."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True, help="Output JSONL path.")
        parser.add_argument("--title", help="Filter by title slug.")
        parser.add_argument("--ruleset-id", help="Filter by exact ruleset id.")
        parser.add_argument("--actor-kind", help="Filter by actor kind.")
        parser.add_argument("--game-type", help="Filter by game type.")
        parser.add_argument("--ladder-type", help="Filter by ranked ladder type.")
        parser.add_argument("--limit", type=int, help="Maximum rows to export.")

    def handle(self, *args, **options):
        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)

        queryset = GameAction.objects.select_related("game", "game__title").order_by(
            "id"
        )

        if options.get("title"):
            queryset = queryset.filter(game__title__slug=options["title"])
        if options.get("ruleset_id"):
            queryset = queryset.filter(ruleset_id=options["ruleset_id"])
        if options.get("actor_kind"):
            queryset = queryset.filter(actor_kind=options["actor_kind"])
        if options.get("game_type"):
            queryset = queryset.filter(game__type=options["game_type"])
        if options.get("ladder_type"):
            queryset = queryset.filter(game__ladder_type=options["ladder_type"])
        if options.get("limit"):
            queryset = queryset[: options["limit"]]

        count = 0
        with output_path.open("w", encoding="utf-8") as output:
            for action in queryset:
                row = {
                    "game_id": action.game_id,
                    "title_slug": action.game.title.slug,
                    "game_type": action.game.type,
                    "ladder_type": action.game.ladder_type,
                    "ruleset_id": action.ruleset_id,
                    "actor_side": action.actor_side,
                    "actor_kind": action.actor_kind,
                    "turn": action.turn,
                    "phase": action.phase,
                    "command": action.command,
                    "legal_commands": action.legal_commands,
                    "observation": action.observation,
                    "pre_state_hash": action.pre_state_hash,
                    "post_state_hash": action.post_state_hash,
                    "outcome": action.outcome,
                    "error": action.error,
                    "final_winner": action.final_winner,
                    "created_at": action.created_at.isoformat(),
                }
                output.write(json.dumps(row, sort_keys=True) + "\n")
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Exported {count} rows to {output_path}"))

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.builder.models import AIPlayer
from apps.collection.models import Deck
from apps.gameplay.agents.policies.model import resolve_model_path


class Command(BaseCommand):
    help = "Configure an AI player to use scripted or local model-backed policy."

    def add_arguments(self, parser):
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--ai-player-id", type=int)
        target.add_argument("--ai-deck-id", type=int)

        parser.add_argument(
            "--policy",
            choices=["scripted", "linear_model"],
            default="linear_model",
        )
        parser.add_argument(
            "--model",
            help=(
                "Checkpoint path for --policy linear_model. Absolute paths and "
                "paths relative to the backend app root are both accepted."
            ),
        )

    def handle(self, *args, **options):
        ai_player = self._get_ai_player(options)
        policy = options["policy"]
        model_path = options.get("model")
        config = dict(ai_player.strategy_config or {})

        if policy == "scripted":
            config["policy"] = "scripted"
            config.pop("model_path", None)
        else:
            if not model_path:
                raise CommandError("--model is required for --policy linear_model")

            resolved_model_path = resolve_model_path(model_path)
            if not resolved_model_path.exists():
                raise CommandError(f"Model checkpoint does not exist: {model_path}")

            config["policy"] = "linear_model"
            config["model_path"] = model_path

        ai_player.strategy_config = config
        ai_player.save(update_fields=["strategy_config", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"AI player {ai_player.id} now uses policy={config['policy']}"
            )
        )
        if config.get("model_path"):
            self.stdout.write(f"model_path={config['model_path']}")

    def _get_ai_player(self, options) -> AIPlayer:
        if options.get("ai_player_id"):
            try:
                return AIPlayer.objects.get(id=options["ai_player_id"])
            except AIPlayer.DoesNotExist as exc:
                raise CommandError(
                    f"AI player {options['ai_player_id']} does not exist."
                ) from exc

        try:
            deck = Deck.objects.select_related("ai_player").get(
                id=options["ai_deck_id"]
            )
        except Deck.DoesNotExist as exc:
            raise CommandError(f"Deck {options['ai_deck_id']} does not exist.") from exc
        if not deck.ai_player:
            raise CommandError(f"Deck {deck.id} is not an AI deck.")
        return deck.ai_player

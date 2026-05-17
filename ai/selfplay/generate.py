from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai.selfplay.runner import PolicySpec, run_selfplay_game, setup_django


def _policy_spec(kind: str, model_path: str | None) -> PolicySpec:
    return PolicySpec(kind=kind, model_path=model_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate local Archetype self-play replay JSONL."
    )
    parser.add_argument("--deck-a", type=int, required=True)
    parser.add_argument("--deck-b", type=int, required=True)
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--max-decisions", type=int, default=300)
    parser.add_argument("--output", required=True)
    parser.add_argument("--append", action="store_true")
    parser.add_argument(
        "--policy-a",
        choices=["scripted", "random", "model"],
        default="scripted",
    )
    parser.add_argument(
        "--policy-b",
        choices=["scripted", "random", "model"],
        default="scripted",
    )
    parser.add_argument("--model-a")
    parser.add_argument("--model-b")
    parser.add_argument(
        "--no-randomize-starting-player",
        action="store_true",
        help="Keep deck A as side_a and deck B as side_b.",
    )
    parser.add_argument(
        "--keep-games",
        action="store_true",
        help="Keep the temporary Game row. Only supported for one game.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.keep_games and args.games > 1:
        raise SystemExit("--keep-games only supports one game at a time.")

    setup_django()

    from apps.collection.models import Deck

    deck_a = Deck.objects.get(id=args.deck_a)
    deck_b = Deck.objects.get(id=args.deck_b)
    if deck_a.title_id != deck_b.title_id:
        raise SystemExit("Decks must belong to the same title.")

    policy_a = _policy_spec(args.policy_a, args.model_a)
    policy_b = _policy_spec(args.policy_b, args.model_b)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.append else "w"

    summaries = []
    with output_path.open(mode, encoding="utf-8") as output:
        for game_index in range(1, args.games + 1):
            result = run_selfplay_game(
                deck_a=deck_a,
                deck_b=deck_b,
                policy_a=policy_a,
                policy_b=policy_b,
                game_index=game_index,
                max_decisions=args.max_decisions,
                randomize_starting_player=not args.no_randomize_starting_player,
                keep_game=args.keep_games,
            )
            for row in result.rows:
                output.write(json.dumps(row, sort_keys=True) + "\n")
            summaries.append(result)
            print(
                f"game={game_index} "
                f"winner={result.winner} "
                f"decisions={result.decisions} "
                f"reason={result.terminal_reason}"
            )

    total_rows = sum(result.decisions for result in summaries)
    print(f"wrote rows={total_rows} output={output_path}")


if __name__ == "__main__":
    main()

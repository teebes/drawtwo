from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ai.selfplay.runner import PolicySpec, run_selfplay_game, setup_django


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a trained linear policy against a baseline."
    )
    parser.add_argument("--deck-a", type=int, required=True)
    parser.add_argument("--deck-b", type=int, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--opponent",
        choices=["scripted", "random", "model"],
        default="scripted",
    )
    parser.add_argument("--opponent-model")
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--max-decisions", type=int, default=300)
    parser.add_argument(
        "--model-side",
        choices=["side_a", "side_b", "alternate"],
        default="alternate",
    )
    parser.add_argument(
        "--output",
        help="Optional JSONL path for evaluated game rows.",
    )
    return parser.parse_args()


def _side_for_game(model_side: str, game_index: int) -> str:
    if model_side != "alternate":
        return model_side
    return "side_a" if game_index % 2 == 1 else "side_b"


def main() -> None:
    args = parse_args()
    setup_django()

    from apps.collection.models import Deck

    deck_a = Deck.objects.get(id=args.deck_a)
    deck_b = Deck.objects.get(id=args.deck_b)
    if deck_a.title_id != deck_b.title_id:
        raise SystemExit("Decks must belong to the same title.")

    model_policy = PolicySpec(kind="model", model_path=args.model)
    opponent_policy = PolicySpec(
        kind=args.opponent,
        model_path=args.opponent_model,
    )

    output_file = None
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_file = output_path.open("w", encoding="utf-8")

    outcomes = Counter()
    winners = Counter()
    decision_counts = []

    try:
        for game_index in range(1, args.games + 1):
            model_side = _side_for_game(args.model_side, game_index)
            if model_side == "side_a":
                policy_a = model_policy
                policy_b = opponent_policy
            else:
                policy_a = opponent_policy
                policy_b = model_policy

            result = run_selfplay_game(
                deck_a=deck_a,
                deck_b=deck_b,
                policy_a=policy_a,
                policy_b=policy_b,
                game_index=game_index,
                max_decisions=args.max_decisions,
                randomize_starting_player=False,
            )
            winners[result.winner] += 1
            decision_counts.append(result.decisions)

            if result.winner == model_side:
                outcomes["wins"] += 1
            elif result.winner == "none":
                outcomes["draws"] += 1
            else:
                outcomes["losses"] += 1

            if output_file:
                for row in result.rows:
                    row["evaluation_model_side"] = model_side
                    output_file.write(json.dumps(row, sort_keys=True) + "\n")

            print(
                f"game={game_index} "
                f"model_side={model_side} "
                f"winner={result.winner} "
                f"decisions={result.decisions} "
                f"reason={result.terminal_reason}"
            )
    finally:
        if output_file:
            output_file.close()

    games = sum(outcomes.values())
    win_rate = outcomes["wins"] / games if games else 0.0
    average_decisions = (
        sum(decision_counts) / len(decision_counts) if decision_counts else 0.0
    )
    print(
        "summary "
        f"games={games} "
        f"wins={outcomes['wins']} "
        f"losses={outcomes['losses']} "
        f"draws={outcomes['draws']} "
        f"win_rate={win_rate:.3f} "
        f"avg_decisions={average_decisions:.1f} "
        f"winners={dict(winners)}"
    )


if __name__ == "__main__":
    main()

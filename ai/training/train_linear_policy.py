from __future__ import annotations

import argparse
from pathlib import Path

from ai.data.replays import iter_replay_decisions
from ai.models.linear_policy import train_linear_policy_streaming


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a dependency-free linear command-ranking policy."
    )
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="Replay JSONL path. Can be passed more than once.",
    )
    parser.add_argument("--output", required=True, help="Output model JSON path.")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--learning-rate", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--shuffle-buffer",
        type=int,
        default=512,
        help=(
            "Number of replay rows to keep in memory for approximate shuffling. "
            "Higher values shuffle better but use more memory."
        ),
    )
    parser.add_argument(
        "--accuracy-limit",
        type=int,
        help="Only use the first N rows for the final training-accuracy pass.",
    )
    parser.add_argument("--title", help="Only train on rows for this title slug.")
    parser.add_argument("--actor-kind", help="Only train on rows for this actor kind.")
    parser.add_argument(
        "--include-rejected",
        action="store_true",
        help="Include rejected rows. Usually leave this off for policy imitation.",
    )
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="Keep replay rows in file order on every epoch.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_paths = [Path(path) for path in args.input]
    shuffle_buffer_size = 0 if args.no_shuffle else args.shuffle_buffer

    def decision_iter():
        return iter_replay_decisions(
            input_paths,
            accepted_only=not args.include_rejected,
            actor_kind=args.actor_kind,
            title=args.title,
            limit=args.limit,
        )

    model, stats = train_linear_policy_streaming(
        decision_iter,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        shuffle_buffer_size=shuffle_buffer_size,
        seed=args.seed,
        accuracy_limit=args.accuracy_limit,
        metadata={
            "input_paths": [str(path) for path in input_paths],
            "title_filter": args.title,
            "actor_kind_filter": args.actor_kind,
            "limit": args.limit,
        },
    )
    model.save(args.output)
    print(
        "trained "
        f"rows_loaded={stats.rows_seen} "
        f"rows_used={stats.rows_used} "
        f"rows_skipped={stats.rows_skipped} "
        f"updates={stats.updates} "
        f"training_accuracy={stats.final_accuracy:.3f} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()

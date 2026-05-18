from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ai.data.replays import ReplayDecision, iter_replay_decisions
from ai.models.linear_policy import train_linear_policy_streaming


def _row(command: dict, legal_commands: list[dict], *, outcome: str = "accepted"):
    return {
        "actor_side": "side_a",
        "command": command,
        "legal_commands": legal_commands,
        "observation": {
            "side": "side_a",
            "public_state": {
                "phase": "main",
                "turn": 1,
                "board": {"side_a": [], "side_b": []},
                "cards": {},
                "creatures": {},
                "deck_counts": {"side_a": 20, "side_b": 20},
                "decks": {"side_a": [], "side_b": []},
                "hand_counts": {"side_a": 3, "side_b": 3},
                "hands": {"side_a": [], "side_b": []},
                "heroes": {
                    "side_a": {
                        "health": 30,
                        "hero_id": "hero_a",
                        "template_slug": "healer",
                    },
                    "side_b": {
                        "health": 30,
                        "hero_id": "hero_b",
                        "template_slug": "sniper",
                    },
                },
                "mana_pool": {"side_a": 1, "side_b": 1},
                "mana_used": {"side_a": 0, "side_b": 0},
            },
        },
        "outcome": outcome,
        "title_slug": "archetype",
    }


class ReplayStreamingTests(unittest.TestCase):
    def test_iter_replay_decisions_filters_and_limits(self):
        legal_commands = [{"type": "cmd_end_turn"}]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "replays.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps(_row(legal_commands[0], legal_commands)),
                        json.dumps(
                            _row(
                                legal_commands[0],
                                legal_commands,
                                outcome="rejected",
                            )
                        ),
                        json.dumps(_row(legal_commands[0], legal_commands)),
                    ]
                ),
                encoding="utf-8",
            )

            decisions = list(iter_replay_decisions([path], limit=1))

        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].line_number, 1)

    def test_streaming_trainer_reopens_data_each_epoch(self):
        legal_commands = [
            {"type": "cmd_end_turn"},
            {
                "type": "cmd_use_hero",
                "hero_id": "hero_a",
                "target_type": "hero",
                "target_id": "hero_b",
            },
        ]
        decisions = [
            _row(legal_commands[1], legal_commands),
            _row(legal_commands[1], legal_commands),
            _row(legal_commands[0], legal_commands),
        ]
        calls = 0

        def decision_iter():
            nonlocal calls
            calls += 1
            return (
                ReplayDecision(row=row, source_path="memory", line_number=index)
                for index, row in enumerate(decisions, start=1)
            )

        model, stats = train_linear_policy_streaming(
            decision_iter,
            epochs=2,
            learning_rate=0.1,
            shuffle_buffer_size=2,
            seed=0,
        )

        self.assertEqual(calls, 3)
        self.assertEqual(stats.rows_seen, 3)
        self.assertEqual(stats.rows_used, 3)
        self.assertEqual(stats.rows_skipped, 0)
        self.assertGreater(model.metadata["weight_count"], 0)
        self.assertEqual(model.metadata["training_mode"], "streaming")


if __name__ == "__main__":
    unittest.main()

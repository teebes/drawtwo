from __future__ import annotations

import tempfile
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from django.core.management import call_command
from django.test import TestCase

from ai.models.linear_policy import LinearPolicyModel
from apps.builder.models import AIPlayer
from apps.gameplay.agents.policies.model import LinearModelPolicy
from apps.gameplay.ai import AIMoveChooser
from apps.gameplay.schemas.commands import AttackCommand, EndTurnCommand
from apps.gameplay.tests.test_agents import make_agent_test_state


class LinearModelPolicyTests(TestCase):
    def test_linear_model_policy_selects_from_legal_commands(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "model.json"
            LinearPolicyModel(weights={"cmd:attack_face": 10.0}).save(model_path)

            state = make_agent_test_state()
            policy = LinearModelPolicy(str(model_path))
            command = policy.select_command(
                state,
                [
                    EndTurnCommand(),
                    AttackCommand(
                        card_id="creature_a_1",
                        target_type="hero",
                        target_id="hero_b",
                    ),
                ],
            )

        self.assertIsInstance(command, AttackCommand)
        self.assertEqual(command.target_id, "hero_b")

    def test_ai_move_chooser_uses_model_policy_from_ai_player_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "model.json"
            LinearPolicyModel(weights={"cmd:attack_face": 10.0}).save(model_path)

            deck = SimpleNamespace(
                script={},
                ai_player=SimpleNamespace(
                    strategy_config={
                        "policy": "linear_model",
                        "model_path": str(model_path),
                    }
                ),
            )
            state = make_agent_test_state()
            decision = AIMoveChooser.choose_decision(state, deck)

        self.assertEqual(decision.actor_kind, "model_ai")
        self.assertIsInstance(decision.command, AttackCommand)
        self.assertEqual(AIMoveChooser.actor_kind_for_deck(deck), "model_ai")

    def test_ai_move_chooser_falls_back_to_scripted_when_model_fails(self):
        deck = SimpleNamespace(
            script={},
            ai_player=SimpleNamespace(
                strategy_config={
                    "policy": "linear_model",
                    "model_path": "/does/not/exist.json",
                }
            ),
        )
        state = make_agent_test_state()

        decision = AIMoveChooser.choose_decision(state, deck)

        self.assertEqual(decision.actor_kind, "scripted_ai")
        self.assertIsNotNone(decision.command)
        self.assertIn("does/not/exist", decision.error)

    def test_set_ai_policy_command_updates_strategy_config(self):
        ai_player = AIPlayer.objects.create(name="Model AI")
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "model.json"
            LinearPolicyModel(weights={"cmd:attack_face": 10.0}).save(model_path)
            stdout = StringIO()

            call_command(
                "set_ai_policy",
                "--ai-player-id",
                str(ai_player.id),
                "--policy",
                "linear_model",
                "--model",
                str(model_path),
                stdout=stdout,
            )

        ai_player.refresh_from_db()
        self.assertEqual(ai_player.strategy_config["policy"], "linear_model")
        self.assertEqual(ai_player.strategy_config["model_path"], str(model_path))

        call_command(
            "set_ai_policy",
            "--ai-player-id",
            str(ai_player.id),
            "--policy",
            "scripted",
            stdout=StringIO(),
        )

        ai_player.refresh_from_db()
        self.assertEqual(ai_player.strategy_config["policy"], "scripted")
        self.assertNotIn("model_path", ai_player.strategy_config)

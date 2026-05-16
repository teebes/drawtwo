from apps.builder.schemas import DeckScript
from apps.gameplay.schemas.commands import (
    AttackCommand,
    Command,
    EndTurnCommand,
    MulliganCommand,
    PlayCardCommand,
    UseHeroCommand,
)
from apps.gameplay.schemas.game import GameState, deterministic_choice


class ScriptedPolicy:
    """
    Command-level replacement for the old rule-based PvE AI.

    The policy intentionally remains simple. Its main job is to keep existing
    PvE behavior working while the stronger search/model policies are built on
    top of the same legal-command interface.
    """

    def __init__(self, script: DeckScript | None = None):
        self.script = script or DeckScript()

    def select_command(
        self,
        state: GameState,
        legal_commands: list[Command],
        budget_ms: int = 100,
    ) -> Command | None:
        if not legal_commands:
            return None

        mulligans = [cmd for cmd in legal_commands if isinstance(cmd, MulliganCommand)]
        if mulligans:
            keep_hand = next((cmd for cmd in mulligans if not cmd.card_ids), None)
            return keep_hand or mulligans[0]

        hero_commands = [
            cmd for cmd in legal_commands if isinstance(cmd, UseHeroCommand)
        ]
        if hero_commands:
            return deterministic_choice(state, hero_commands, "scripted_hero_power")

        spell_commands = [
            cmd
            for cmd in legal_commands
            if isinstance(cmd, PlayCardCommand)
            and state.cards.get(cmd.card_id)
            and state.cards[cmd.card_id].card_type == "spell"
        ]
        if spell_commands:
            return deterministic_choice(state, spell_commands, "scripted_spell")

        creature_commands = [
            cmd
            for cmd in legal_commands
            if isinstance(cmd, PlayCardCommand)
            and state.cards.get(cmd.card_id)
            and state.cards[cmd.card_id].card_type == "creature"
        ]
        if creature_commands:
            return creature_commands[0]

        attack_commands = [
            cmd for cmd in legal_commands if isinstance(cmd, AttackCommand)
        ]
        if attack_commands:
            if self.script.strategy == "rush":
                hero_attacks = [
                    cmd for cmd in attack_commands if cmd.target_type == "hero"
                ]
                if hero_attacks:
                    return hero_attacks[0]
            if self.script.strategy == "control":
                board_attacks = [
                    cmd for cmd in attack_commands if cmd.target_type == "creature"
                ]
                if board_attacks:
                    return deterministic_choice(
                        state, board_attacks, "scripted_control_attack"
                    )
            return deterministic_choice(state, attack_commands, "scripted_attack")

        end_turn = next(
            (cmd for cmd in legal_commands if isinstance(cmd, EndTurnCommand)),
            None,
        )
        return end_turn or legal_commands[0]

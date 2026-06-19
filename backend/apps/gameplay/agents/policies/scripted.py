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

TargetSpec = str | dict | None


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

        opening_command = self._select_opening_command(state, legal_commands)
        if opening_command:
            return opening_command

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

    def _select_opening_command(
        self,
        state: GameState,
        legal_commands: list[Command],
    ) -> Command | None:
        opening = self.script.opening or []
        for turn_script in opening:
            if not isinstance(turn_script, dict):
                continue
            script_turn = turn_script.get("turn", turn_script.get("round"))
            if script_turn != state.turn:
                continue

            for raw_command in turn_script.get("commands", []):
                command = self._match_opening_command(
                    state,
                    legal_commands,
                    raw_command,
                )
                if command:
                    return command
        return None

    def _match_opening_command(
        self,
        state: GameState,
        legal_commands: list[Command],
        raw_command,
    ) -> Command | None:
        if raw_command == "use_hero_power":
            return next(
                (cmd for cmd in legal_commands if isinstance(cmd, UseHeroCommand)),
                None,
            )

        if raw_command == "end_turn":
            return next(
                (cmd for cmd in legal_commands if isinstance(cmd, EndTurnCommand)),
                None,
            )

        if not isinstance(raw_command, dict):
            return None

        if "play_card" in raw_command:
            return self._match_play_card_command(
                state,
                legal_commands,
                raw_command.get("play_card") or {},
            )

        if "attack" in raw_command:
            return self._match_attack_command(
                state,
                legal_commands,
                raw_command.get("attack") or {},
            )

        return None

    def _match_play_card_command(
        self,
        state: GameState,
        legal_commands: list[Command],
        spec,
    ) -> Command | None:
        if isinstance(spec, str):
            spec = {"slug": spec}
        if not isinstance(spec, dict):
            return None

        slug = spec.get("slug")
        candidates = [
            cmd
            for cmd in legal_commands
            if isinstance(cmd, PlayCardCommand)
            and state.cards.get(cmd.card_id)
            and (not slug or state.cards[cmd.card_id].template_slug == slug)
        ]
        target_type, target_id = self._resolve_target(state, spec.get("target"))
        if target_id:
            candidates = [
                cmd
                for cmd in candidates
                if cmd.target_type == target_type and cmd.target_id == target_id
            ]
        return candidates[0] if candidates else None

    def _match_attack_command(
        self,
        state: GameState,
        legal_commands: list[Command],
        spec,
    ) -> Command | None:
        if not isinstance(spec, dict):
            return None

        candidates = [cmd for cmd in legal_commands if isinstance(cmd, AttackCommand)]
        _, attacker_id = self._resolve_target(state, spec.get("attacker"))
        if attacker_id:
            candidates = [cmd for cmd in candidates if cmd.card_id == attacker_id]

        target = spec.get("target")
        if target == "enemy_taunt_else_hero":
            hero_attacks = [cmd for cmd in candidates if cmd.target_type == "hero"]
            if hero_attacks:
                return hero_attacks[0]
            creature_attacks = [
                cmd for cmd in candidates if cmd.target_type == "creature"
            ]
            return creature_attacks[0] if creature_attacks else None

        target_type, target_id = self._resolve_target(state, target)
        if target_id:
            candidates = [
                cmd
                for cmd in candidates
                if cmd.target_type == target_type and cmd.target_id == target_id
            ]
        return candidates[0] if candidates else None

    def _resolve_target(
        self,
        state: GameState,
        target: TargetSpec,
    ) -> tuple[str | None, str | None]:
        if not target:
            return None, None

        own_side = state.active
        enemy_side = state.opposite_side

        if isinstance(target, dict):
            return self._resolve_structured_target(state, target)

        if target == "own_first_creature":
            creature_id = next(iter(state.board.get(own_side, [])), None)
            return ("creature", creature_id) if creature_id else (None, None)

        if target == "enemy_first_creature":
            creature_id = next(iter(state.board.get(enemy_side, [])), None)
            return ("creature", creature_id) if creature_id else (None, None)

        if target == "enemy_hero":
            hero = state.heroes.get(enemy_side)
            return ("hero", hero.hero_id) if hero else (None, None)

        if target == "own_hero":
            hero = state.heroes.get(own_side)
            return ("hero", hero.hero_id) if hero else (None, None)

        return None, None

    def _resolve_structured_target(
        self,
        state: GameState,
        target: dict,
    ) -> tuple[str | None, str | None]:
        target_type = target.get("type", "creature")
        side_selector = target.get("side", "own")
        if side_selector == "own":
            side = state.active
        elif side_selector in ("enemy", "opponent"):
            side = state.opposite_side
        else:
            return None, None

        if target_type == "hero":
            hero = state.heroes.get(side)
            return ("hero", hero.hero_id) if hero else (None, None)

        if target_type != "creature":
            return None, None

        for creature_id in state.board.get(side, []):
            creature = state.creatures.get(creature_id)
            if not creature:
                continue
            if not self._creature_matches_structured_target(state, creature, target):
                continue
            return "creature", creature_id
        return None, None

    def _creature_matches_structured_target(
        self,
        state: GameState,
        creature,
        target: dict,
    ) -> bool:
        card = state.cards.get(creature.card_id)
        template_slug = target.get("template_slug")
        if template_slug and (not card or card.template_slug != template_slug):
            return False
        if "attack" in target and creature.attack != target["attack"]:
            return False
        if "health" in target and creature.health != target["health"]:
            return False
        return True

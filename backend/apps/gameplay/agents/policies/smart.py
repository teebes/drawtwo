"""
Simulation-based "smart" AI policy.

Unlike the scripted strategies (rush/control/...), this policy does not encode
any playstyle. Each turn it enumerates the legal commands, resolves every
candidate through the real engine against a copy of the game state
(`apply_command`), and greedily plays whichever command most improves a
generic evaluation of the resulting state.

Because candidates are resolved by the engine itself, everything the ruleset
supports — battlecries, deathrattles, taunt restrictions, cleave adjacency,
summons, and any trigger or action added later — is automatically reflected in
the outcome being scored. The evaluation function only needs to judge *states*
(hero health, board material, card advantage), not to understand mechanics.
"""

import logging
import math
import time
from typing import Iterable

from pydantic import TypeAdapter, ValidationError

from apps.builder.schemas import Action, DeckScript
from apps.gameplay.agents.policies.scripted import ScriptedPolicy
from apps.gameplay.agents.simulator import apply_command
from apps.gameplay.schemas.commands import (
    Command,
    ConcedeCommand,
    EndTurnCommand,
    MulliganCommand,
)
from apps.gameplay.schemas.game import Creature, GameState, HeroInPlay

logger = logging.getLogger(__name__)

WIN_SCORE = 1_000_000.0

# A command must beat "do nothing" by at least this much to be worth playing;
# otherwise the policy ends the turn.
MIN_IMPROVEMENT = 0.05

# Cards costing more than this are thrown back during mulligan.
MULLIGAN_KEEP_MAX_COST = 3

_SCOPE_MULTIPLIER = {"single": 1.0, "cleave": 1.6, "all": 2.5}

# How much pending trait actions are worth, by trigger. Battlecries have
# already fired for creatures on the board; deathrattles are still live value.
_TRAIT_ACTION_WEIGHT = {"battlecry": 0.0, "deathrattle": 0.7}
_DEFAULT_TRAIT_ACTION_WEIGHT = 0.5

# Flat bonuses for keyword traits without actions. Unknown (future) traits get
# a small default bonus so the policy never treats new mechanics as worthless.
_TRAIT_FLAT_BONUS = {
    "battlecry": 0.0,
    "charge": 0.0,  # spent once the creature is on the board
    "deathrattle": 0.0,
    "unique": 0.0,
    "stealth": 0.5,
    "taunt": 0.5,
    "armor": 1.0,
    "inspire": 1.0,
}
_DEFAULT_TRAIT_FLAT_BONUS = 0.5


def _opposing(side: str) -> str:
    return "side_b" if side == "side_a" else "side_a"


def _action_score(action: Action) -> float:
    """Generic value of one pending action, used for deathrattles and future
    trigger-carried actions."""
    scope = _SCOPE_MULTIPLIER.get(getattr(action, "scope", "single"), 1.0)
    amount = getattr(action, "amount", 1) or 0
    kind = getattr(action, "action", "")

    if kind == "damage":
        return amount * scope
    if kind == "heal":
        return 0.5 * amount * scope
    if kind == "buff":
        return amount * scope
    if kind == "draw":
        return 1.5 * amount
    if kind == "remove":
        return 4.0 * scope
    if kind == "clear":
        return 5.0
    if kind == "summon":
        return 2.5
    if kind == "temp_mana_boost":
        return 0.5 * amount
    return 1.0


def _trait_action_sum(trait) -> float:
    total = 0.0
    for raw_action in getattr(trait, "actions", None) or []:
        try:
            action = TypeAdapter(Action).validate_python(raw_action)
        except ValidationError:
            continue
        total += _action_score(action)
    return total


def _creature_score(creature: Creature) -> float:
    attack = max(creature.attack, 0)
    health = max(creature.health, 0)
    score = attack + 0.9 * health

    for trait in creature.traits or []:
        trait_type = trait.type
        score += _TRAIT_FLAT_BONUS.get(trait_type, _DEFAULT_TRAIT_FLAT_BONUS)
        score += _trait_action_sum(trait) * _TRAIT_ACTION_WEIGHT.get(
            trait_type, _DEFAULT_TRAIT_ACTION_WEIGHT
        )
        if trait_type == "taunt":
            score += 0.15 * health
        elif trait_type in ("lifesteal", "ranged", "cleave"):
            score += 0.4 * attack

    return score


def _hero_score(hero: HeroInPlay | None) -> float:
    if hero is None:
        return 0.0
    health = max(hero.health, 0)
    # Concave in health: a point of damage matters more the lower the hero is,
    # so the policy protects a weakened hero and pushes lethal setups.
    return 2.0 * health + 4.0 * math.sqrt(health)


def evaluate_state(state: GameState, side: str) -> float:
    """Score a state from `side`'s perspective. Higher is better."""
    enemy = _opposing(side)

    if state.winner == side:
        return WIN_SCORE
    if state.winner == enemy:
        return -WIN_SCORE

    score = _hero_score(state.heroes.get(side)) - _hero_score(state.heroes.get(enemy))

    for creature_id in state.board.get(side, []):
        creature = state.creatures.get(creature_id)
        if creature:
            score += _creature_score(creature)
    # Enemy creatures are weighted above our own: they attack on a turn this
    # one-command lookahead never sees, so removal is worth more than parity.
    for creature_id in state.board.get(enemy, []):
        creature = state.creatures.get(creature_id)
        if creature:
            score -= 1.2 * _creature_score(creature)

    # Card advantage; the small deck term makes overdrawing into a full hand
    # (burned cards) read as a loss.
    score += 1.5 * len(state.hands.get(side, []))
    score -= 1.5 * len(state.hands.get(enemy, []))
    score += 0.1 * min(len(state.decks.get(side, [])), 10)
    score -= 0.1 * min(len(state.decks.get(enemy, [])), 10)

    # Slight value on unspent mana mid-turn so effects like temporary mana
    # boosts register as progress even before the extra mana is used.
    if state.active == side and state.phase == "main":
        available = state.mana_pool.get(side, 0) - state.mana_used.get(side, 0)
        score += 0.15 * max(available, 0)

    return score


class SmartPolicy:
    """
    Greedy one-command lookahead using the engine simulator.

    The live AI loop asks for one command at a time, so repeatedly picking the
    best single command plays out the whole turn.
    """

    def __init__(self, script: DeckScript | None = None):
        self.script = script or DeckScript()
        # Reused for scripted openings and as a fallback if simulation fails.
        self._scripted = ScriptedPolicy(self.script)

    def select_command(
        self,
        state: GameState,
        legal_commands: list[Command],
        budget_ms: int = 1000,
    ) -> Command | None:
        if not legal_commands:
            return None
        try:
            return self._select(state, legal_commands, budget_ms)
        except Exception:
            logger.exception("SmartPolicy failed; falling back to scripted policy")
            return self._scripted.select_command(state, legal_commands, budget_ms)

    def _select(
        self,
        state: GameState,
        legal_commands: list[Command],
        budget_ms: int,
    ) -> Command | None:
        mulligans = [cmd for cmd in legal_commands if isinstance(cmd, MulliganCommand)]
        if mulligans:
            return self._select_mulligan(state, mulligans)

        opening_command = self._scripted._select_opening_command(state, legal_commands)
        if opening_command:
            return opening_command

        side = state.active
        baseline = evaluate_state(state, side)
        end_turn = next(
            (cmd for cmd in legal_commands if isinstance(cmd, EndTurnCommand)),
            None,
        )
        candidates = [
            cmd
            for cmd in legal_commands
            if not isinstance(cmd, (EndTurnCommand, ConcedeCommand, MulliganCommand))
        ]

        deadline = time.monotonic() + max(budget_ms, 100) / 1000.0
        best_command: Command | None = None
        best_score = baseline + MIN_IMPROVEMENT
        evaluated = 0

        for command in self._ordered_candidates(candidates):
            if evaluated > 0 and time.monotonic() > deadline:
                break

            result = apply_command(state, side, command)
            evaluated += 1

            if result.post_state_hash == result.pre_state_hash:
                # Rejected or otherwise a no-op; nothing to gain.
                continue

            if result.winner == side:
                return command

            score = evaluate_state(result.state, side)
            if score > best_score:
                best_score = score
                best_command = command

        if best_command:
            return best_command
        return end_turn or legal_commands[0]

    def _ordered_candidates(self, commands: list[Command]) -> Iterable[Command]:
        """
        Order candidates so one representative of each (command, actor, target)
        group is simulated before positional duplicates. Board position rarely
        changes the outcome, so if the time budget truncates the search it
        should truncate the near-duplicates first.
        """
        primary: list[Command] = []
        secondary: list[Command] = []
        seen: set[tuple] = set()
        for command in commands:
            key = (
                command.type,
                getattr(command, "card_id", None) or getattr(command, "hero_id", None),
                getattr(command, "target_type", None),
                getattr(command, "target_id", None),
            )
            if key in seen:
                secondary.append(command)
            else:
                seen.add(key)
                primary.append(command)
        return primary + secondary

    def _select_mulligan(
        self,
        state: GameState,
        mulligans: list[MulliganCommand],
    ) -> Command:
        """
        Throw back expensive cards to smooth the opening curve.

        Mulligan redraws are resolved with the state's deterministic RNG, so
        simulating them would amount to peeking at the replacement cards;
        a curve heuristic keeps the policy honest.
        """
        options = max(mulligans, key=lambda cmd: len(cmd.card_ids)).card_ids
        toss = {
            card_id
            for card_id in options
            if state.cards.get(card_id)
            and state.cards[card_id].cost > MULLIGAN_KEEP_MAX_COST
        }
        for command in mulligans:
            if set(command.card_ids) == toss:
                return command
        keep_hand = next((cmd for cmd in mulligans if not cmd.card_ids), None)
        return keep_hand or mulligans[0]

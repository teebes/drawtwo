"""Consistent results for immutable composition captures."""

from django.db.models import Count, F, Q

from apps.gameplay.models import GameLoadout


def _empty_composition_record() -> dict:
    return {
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "games": 0,
        "win_rate": 0.0,
    }


def _record_composition_result(record: dict, result: str) -> None:
    record[result] += 1
    record["games"] += 1
    record["win_rate"] = round(record["wins"] / record["games"], 4)


def _result_for_loadout(loadout: GameLoadout) -> str:
    """Return wins/losses/draws from this loadout's point of view."""

    game = loadout.game
    winner_side = (game.state or {}).get("winner")

    # Every normally completed captured game has winner side in state. Keep the
    # FK fallback for tests and manually finalized games, while avoiding a guess
    # if both sides somehow point to the same source deck.
    if winner_side not in {GameLoadout.SIDE_A, GameLoadout.SIDE_B} and game.winner_id:
        if game.side_a_id != game.side_b_id:
            if game.winner_id == game.side_a_id:
                winner_side = GameLoadout.SIDE_A
            elif game.winner_id == game.side_b_id:
                winner_side = GameLoadout.SIDE_B

    if winner_side == loadout.side:
        return "wins"
    if winner_side in {GameLoadout.SIDE_A, GameLoadout.SIDE_B}:
        return "losses"
    return "draws"


def composition_result_counts() -> dict:
    """Shared SQL result expressions for headlines and grouped statistics."""

    valid_state_winner = Q(
        game__state__winner__in=[GameLoadout.SIDE_A, GameLoadout.SIDE_B]
    )
    state_win = Q(
        side=GameLoadout.SIDE_A,
        game__state__winner=GameLoadout.SIDE_A,
    ) | Q(
        side=GameLoadout.SIDE_B,
        game__state__winner=GameLoadout.SIDE_B,
    )
    state_loss = Q(
        side=GameLoadout.SIDE_A,
        game__state__winner=GameLoadout.SIDE_B,
    ) | Q(
        side=GameLoadout.SIDE_B,
        game__state__winner=GameLoadout.SIDE_A,
    )

    # A winner FK predates the side value in state for a few manually finalized
    # games. It is unambiguous only when the two source decks are different.
    fallback_available = (
        (~valid_state_winner | Q(game__state__winner__isnull=True))
        & Q(game__winner_id__isnull=False)
        & ~Q(game__side_a_id=F("game__side_b_id"))
    )
    fallback_win = fallback_available & (
        Q(
            side=GameLoadout.SIDE_A,
            game__winner_id=F("game__side_a_id"),
        )
        | Q(
            side=GameLoadout.SIDE_B,
            game__winner_id=F("game__side_b_id"),
        )
    )
    fallback_loss = fallback_available & (
        Q(
            side=GameLoadout.SIDE_A,
            game__winner_id=F("game__side_b_id"),
        )
        | Q(
            side=GameLoadout.SIDE_B,
            game__winner_id=F("game__side_a_id"),
        )
    )

    return {
        "games": Count("id"),
        "wins": Count("id", filter=state_win | fallback_win),
        "losses": Count("id", filter=state_loss | fallback_loss),
    }


def _aggregate_composition_record(loadouts) -> dict:
    return composition_record(loadouts.aggregate(**composition_result_counts()))


def composition_record(totals) -> dict:
    games = totals["games"] or 0
    wins = totals["wins"] or 0
    losses = totals["losses"] or 0
    return {
        "wins": wins,
        "losses": losses,
        "draws": games - wins - losses,
        "games": games,
        "win_rate": round(wins / games, 4) if games else 0.0,
    }

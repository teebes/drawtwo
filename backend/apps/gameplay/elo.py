"""
ELO rating system for PvP matches.
"""
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class ELOCalculator:
    """
    Implements the ELO rating calculation for PvP matches.

    The ELO system is a method for calculating the relative skill levels of players.
    After each match, the winner takes points from the loser. The amount of points
    transferred depends on the rating difference and a K-factor.
    """

    # K-factor determines how much ratings change after each game
    # Higher K-factor = more volatile ratings
    # 32 is standard for chess players under 2400 rating
    K_FACTOR = 32

    @classmethod
    def calculate_expected_score(cls, rating_a: int, rating_b: int) -> float:
        """
        Calculate the expected score for player A against player B.

        Formula: E_a = 1 / (1 + 10^((rating_b - rating_a) / 400))

        Args:
            rating_a: Current ELO rating of player A
            rating_b: Current ELO rating of player B

        Returns:
            Expected score (probability of winning) for player A (0.0 to 1.0)
        """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    @classmethod
    def calculate_new_ratings(
        cls,
        winner_rating: int,
        loser_rating: int,
        k_factor: int = None
    ) -> Tuple[int, int]:
        """
        Calculate new ELO ratings after a match.

        Args:
            winner_rating: Current ELO rating of the winner
            loser_rating: Current ELO rating of the loser
            k_factor: K-factor for rating adjustment (default: cls.K_FACTOR)

        Returns:
            Tuple of (new_winner_rating, new_loser_rating)
        """
        if k_factor is None:
            k_factor = cls.K_FACTOR

        # Calculate expected scores
        winner_expected = cls.calculate_expected_score(winner_rating, loser_rating)
        loser_expected = cls.calculate_expected_score(loser_rating, winner_rating)

        # Winner gets 1 point, loser gets 0 points
        winner_actual = 1.0
        loser_actual = 0.0

        # Calculate rating changes
        winner_change = k_factor * (winner_actual - winner_expected)
        loser_change = k_factor * (loser_actual - loser_expected)

        # Apply changes
        new_winner_rating = int(round(winner_rating + winner_change))
        new_loser_rating = int(round(loser_rating + loser_change))

        # Ensure ratings don't go below a minimum threshold
        new_winner_rating = max(100, new_winner_rating)
        new_loser_rating = max(100, new_loser_rating)

        logger.info(
            f"ELO Update: Winner {winner_rating} -> {new_winner_rating} "
            f"({new_winner_rating - winner_rating:+d}), "
            f"Loser {loser_rating} -> {new_loser_rating} "
            f"({new_loser_rating - loser_rating:+d})"
        )

        return new_winner_rating, new_loser_rating

    @classmethod
    def get_rating_change(
        cls,
        player_rating: int,
        opponent_rating: int,
        player_won: bool,
        k_factor: int = None
    ) -> int:
        """
        Calculate the rating change for a single player.

        Args:
            player_rating: Current ELO rating of the player
            opponent_rating: Current ELO rating of the opponent
            player_won: Whether the player won the match
            k_factor: K-factor for rating adjustment (default: cls.K_FACTOR)

        Returns:
            Rating change (can be negative)
        """
        if player_won:
            new_winner, _ = cls.calculate_new_ratings(player_rating, opponent_rating, k_factor)
            return new_winner - player_rating
        else:
            _, new_loser = cls.calculate_new_ratings(opponent_rating, player_rating, k_factor)
            return new_loser - player_rating

"""Who can name a composition, independent of the current stats filters."""

from django.db.models import Count, Q

from apps.gameplay.composition_records import composition_result_counts
from apps.gameplay.models import Game, GameLoadout


def can_name_composition(title, user, composition):
    if not user or not user.is_authenticated:
        return False
    if title.can_be_edited_by(user):
        return True
    if composition is None or composition.title_id != title.id:
        return False

    # Daily ranked wins come first, then rapid wins break ties. Exact ties
    # qualify; zero wins never do. All time, heroes, and captured decks count.
    win_filter = composition_result_counts()["wins"].filter
    wins = (
        GameLoadout.objects.filter(
            composition=composition,
            game__title=title,
            game__type=Game.GAME_TYPE_RANKED,
            game__status=Game.GAME_STATUS_ENDED,
            player__isnull=False,
        )
        .order_by()
        .values("player_id")
        .annotate(
            daily_wins=Count(
                "id", filter=win_filter & Q(game__ladder_type=Game.LADDER_TYPE_DAILY)
            ),
            rapid_wins=Count(
                "id", filter=win_filter & Q(game__ladder_type=Game.LADDER_TYPE_RAPID)
            ),
        )
        .filter(Q(daily_wins__gt=0) | Q(rapid_wins__gt=0))
    )
    leader = wins.order_by("-daily_wins", "-rapid_wins", "player_id").first()
    if leader is None:
        return False
    if leader["player_id"] == user.id:
        return True
    return wins.filter(
        player_id=user.id,
        daily_wins=leader["daily_wins"],
        rapid_wins=leader["rapid_wins"],
    ).exists()

from django.contrib.auth import get_user_model

from apps.authentication.models import Friendship
from apps.builder.models import Title
from apps.gameplay.models import FriendlyChallenge, Game

User = get_user_model()


def _is_user_action_required(game_state, user_side: str) -> bool:
    if game_state.phase == "mulligan":
        return not game_state.mulligan_done.get(user_side, False)
    return game_state.active == user_side


def get_title_lobby_badge_count(title: Title, user) -> int:
    pending_challenge_count = FriendlyChallenge.objects.filter(
        challengee=user,
        title=title,
        status=FriendlyChallenge.STATUS_PENDING,
    ).count()

    incoming_friend_request_count = (
        Friendship.objects.filter(friend=user, status=Friendship.STATUS_PENDING)
        .exclude(initiated_by=user)
        .count()
    )

    active_games = Game.objects.where_user_is_side(title, user).filter(
        type__in=[
            Game.GAME_TYPE_RANKED,
            Game.GAME_TYPE_FRIENDLY,
            Game.GAME_TYPE_PVE,
        ],
        status=Game.GAME_STATUS_IN_PROGRESS,
    )
    user_turn_game_count = sum(
        1
        for game in active_games
        if _is_user_action_required(game.game_state, game.user_side)
    )

    return (
        pending_challenge_count + incoming_friend_request_count + user_turn_game_count
    )


def get_title_lobby_badge_count_by_slug(user_id: int, title_slug: str) -> int | None:
    if not title_slug:
        return None

    try:
        title = Title.objects.get(slug=title_slug)
        user = User.objects.get(id=user_id)
    except (Title.DoesNotExist, User.DoesNotExist):
        return None

    return get_title_lobby_badge_count(title, user)

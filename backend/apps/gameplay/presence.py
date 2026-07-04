import logging
import time

from django.conf import settings

logger = logging.getLogger(__name__)


DEFAULT_GAME_PRESENCE_TTL_SECONDS = 75

_redis_client = None


def mark_game_connection_active(
    *,
    game_id: int | str,
    user_id: int,
    side: str,
    channel_name: str,
) -> None:
    client = _get_redis_client()
    if client is None:
        return

    ttl_seconds = _presence_ttl_seconds()
    expires_at = time.time() + ttl_seconds
    key = _presence_key(game_id=game_id, user_id=user_id, side=side)

    try:
        client.zadd(key, {channel_name: expires_at})
        client.expire(key, ttl_seconds * 2)
    except Exception as exc:
        logger.warning("Failed to mark game presence for %s: %s", key, exc)


def refresh_game_connection_presence(
    *,
    game_id: int | str,
    user_id: int,
    side: str,
    channel_name: str,
) -> None:
    mark_game_connection_active(
        game_id=game_id,
        user_id=user_id,
        side=side,
        channel_name=channel_name,
    )


def clear_game_connection_presence(
    *,
    game_id: int | str,
    user_id: int,
    side: str,
    channel_name: str,
) -> None:
    client = _get_redis_client()
    if client is None:
        return

    key = _presence_key(game_id=game_id, user_id=user_id, side=side)

    try:
        client.zrem(key, channel_name)
    except Exception as exc:
        logger.warning("Failed to clear game presence for %s: %s", key, exc)


def is_user_live_in_game(*, game_id: int | str, user_id: int, side: str) -> bool:
    client = _get_redis_client()
    if client is None:
        return False

    key = _presence_key(game_id=game_id, user_id=user_id, side=side)
    now = time.time()

    try:
        client.zremrangebyscore(key, "-inf", now)
        return client.zcard(key) > 0
    except Exception as exc:
        logger.warning("Failed to check game presence for %s: %s", key, exc)
        return False


def _presence_key(*, game_id: int | str, user_id: int, side: str) -> str:
    prefix = getattr(settings, "GAMEPLAY_PRESENCE_KEY_PREFIX", "drawtwo:presence")
    return f"{prefix}:game:{game_id}:user:{user_id}:side:{side}"


def _presence_ttl_seconds() -> int:
    return int(
        getattr(
            settings,
            "GAMEPLAY_PRESENCE_TTL_SECONDS",
            DEFAULT_GAME_PRESENCE_TTL_SECONDS,
        )
    )


def _get_redis_client():
    global _redis_client

    url = getattr(settings, "GAMEPLAY_PRESENCE_REDIS_URL", "")
    if not url:
        return None

    if _redis_client is None:
        import redis

        _redis_client = redis.Redis.from_url(
            url,
            socket_timeout=1,
            socket_connect_timeout=1,
            decode_responses=True,
        )

    return _redis_client

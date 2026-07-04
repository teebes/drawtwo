import logging
import time

import jwt
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.gameplay.models import PushDevice, PushNotificationEvent
from apps.gameplay.presence import is_user_live_in_game

logger = logging.getLogger(__name__)

APNS_PRODUCTION_HOST = "https://api.push.apple.com"
APNS_SANDBOX_HOST = "https://api.sandbox.push.apple.com"
APNS_TOKEN_TTL_SECONDS = 50 * 60
APNS_TIMEOUT_SECONDS = 10

_cached_auth_token = None
_cached_auth_token_created_at = 0.0


def normalize_device_token(token: str) -> str:
    return "".join(token.split()).lower()


def register_push_device(
    *,
    user,
    token: str,
    platform: str = PushDevice.PLATFORM_IOS,
    bundle_id: str = "",
    environment: str = PushDevice.ENVIRONMENT_PRODUCTION,
) -> PushDevice:
    token = normalize_device_token(token)
    defaults = {
        "user": user,
        "platform": platform,
        "bundle_id": bundle_id or "",
        "environment": environment,
        "is_active": True,
        "last_seen_at": timezone.now(),
        "last_error": "",
    }
    device, _ = PushDevice.objects.update_or_create(
        token=token,
        environment=environment,
        bundle_id=bundle_id or "",
        defaults=defaults,
    )
    return device


def deactivate_push_device(
    *,
    user,
    token: str,
    environment: str | None = None,
    bundle_id: str | None = None,
) -> int:
    token = normalize_device_token(token)
    devices = PushDevice.objects.filter(user=user, token=token, is_active=True)
    if environment:
        devices = devices.filter(environment=environment)
    if bundle_id is not None:
        devices = devices.filter(bundle_id=bundle_id)
    return devices.update(is_active=False, last_seen_at=timezone.now())


def enqueue_push_notification(
    *,
    user_id: int,
    notification_type: str,
    dedupe_key: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> PushNotificationEvent | None:
    event, created = PushNotificationEvent.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={
            "user_id": user_id,
            "notification_type": notification_type,
            "title": title,
            "body": body,
            "data": data or {},
        },
    )
    if not created:
        return event

    from apps.gameplay.tasks import send_push_notification_event

    transaction.on_commit(lambda: send_push_notification_event.delay(event.id))
    return event


def is_turn_ready_for_side(game_state, side: str) -> bool:
    return game_state.phase == "main" and game_state.active == side


def enqueue_turn_ready_notification(*, game, side: str, game_state):
    if game.status in (game.GAME_STATUS_ENDED, game.GAME_STATUS_ABORTED):
        return None
    if side in game_state.ai_sides:
        return None
    if not is_turn_ready_for_side(game_state, side):
        return None

    user_id = _user_id_for_side(game, side)
    if not user_id:
        return None
    if is_user_live_in_game(game_id=game.id, user_id=user_id, side=side):
        logger.info(
            "Skipping turn-ready push for user %s in game %s because they are live",
            user_id,
            game.id,
        )
        return None

    opponent_name = _opponent_name_for_side(game, side)
    if game.type == game.GAME_TYPE_RANKED:
        ladder_label = game.get_ladder_type_display()
        body = f"Your turn in {ladder_label} ranked against {opponent_name}."
    else:
        body = f"Your turn against {opponent_name}."

    return enqueue_push_notification(
        user_id=user_id,
        notification_type=PushNotificationEvent.TYPE_TURN_READY,
        dedupe_key=(
            f"turn_ready:{game.id}:{user_id}:{game_state.turn}:"
            f"{game_state.phase}:{side}"
        ),
        title="Your turn",
        body=body,
        data={
            "game_id": game.id,
            "title_slug": game.title.slug if game.title_id else "",
            "game_type": game.type,
            "ladder_type": game.ladder_type or "",
            "side": side,
        },
    )


def enqueue_friend_challenge_notification(challenge):
    return enqueue_push_notification(
        user_id=challenge.challengee_id,
        notification_type=PushNotificationEvent.TYPE_FRIEND_CHALLENGE,
        dedupe_key=f"friend_challenge:{challenge.id}:{challenge.challengee_id}",
        title="New challenge",
        body=f"{challenge.challenger.display_name} challenged you to a game.",
        data={
            "challenge_id": challenge.id,
            "title_slug": challenge.title.slug,
            "challenger_id": challenge.challenger_id,
        },
    )


def enqueue_match_started_notification(*, user_id: int, game, ladder_type: str):
    ladder_label = game.get_ladder_type_display()
    return enqueue_push_notification(
        user_id=user_id,
        notification_type=PushNotificationEvent.TYPE_MATCH_STARTED,
        dedupe_key=f"match_started:{game.id}:{user_id}",
        title="Match found",
        body=f"Your {ladder_label} ranked game has started.",
        data={
            "game_id": game.id,
            "title_slug": game.title.slug if game.title_id else "",
            "game_type": game.type,
            "ladder_type": ladder_type,
        },
    )


def send_push_event(event_id: int) -> dict:
    try:
        event = PushNotificationEvent.objects.get(id=event_id)
    except PushNotificationEvent.DoesNotExist:
        return {"sent": 0, "failed": 0, "skipped": 1}

    devices = list(
        PushDevice.objects.filter(user_id=event.user_id, is_active=True).order_by("id")
    )
    if not devices:
        event.sent_at = timezone.now()
        event.last_error = "No active push devices."
        event.save(update_fields=["sent_at", "last_error"])
        return {"sent": 0, "failed": 0, "skipped": 1}

    client = APNsClient()
    if not client.is_configured:
        event.sent_at = timezone.now()
        event.last_error = "APNs is not configured."
        event.save(update_fields=["sent_at", "last_error"])
        logger.info("Skipping APNs push %s because APNs is not configured", event.id)
        return {"sent": 0, "failed": 0, "skipped": len(devices)}

    sent = 0
    failed = 0
    errors = []

    for device in devices:
        try:
            client.send_alert(
                device=device,
                title=event.title,
                body=event.body,
                data={
                    "notification_type": event.notification_type,
                    **(event.data or {}),
                },
                badge_count=_badge_count_for_event(event),
            )
            sent += 1
            if device.last_error:
                device.last_error = ""
                device.save(update_fields=["last_error"])
        except APNsPermanentDeviceError as exc:
            failed += 1
            device.is_active = False
            device.last_error = str(exc)
            device.save(update_fields=["is_active", "last_error"])
            errors.append(str(exc))
        except Exception as exc:
            failed += 1
            device.last_error = str(exc)
            device.save(update_fields=["last_error"])
            errors.append(str(exc))
            logger.warning("Failed to send APNs push event %s: %s", event.id, exc)

    event.sent_at = timezone.now()
    event.last_error = "; ".join(errors)[:1000]
    event.save(update_fields=["sent_at", "last_error"])
    return {"sent": sent, "failed": failed, "skipped": 0}


class APNsError(Exception):
    pass


class APNsPermanentDeviceError(APNsError):
    pass


class APNsClient:
    @property
    def is_configured(self) -> bool:
        return bool(
            settings.APNS_TEAM_ID
            and settings.APNS_KEY_ID
            and (settings.APNS_AUTH_KEY or settings.APNS_AUTH_KEY_PATH)
        )

    def send_alert(
        self,
        *,
        device: PushDevice,
        title: str,
        body: str,
        data: dict,
        badge_count: int | None = None,
    ):
        topic = device.bundle_id or settings.APNS_TOPIC
        if not topic:
            raise APNsError("APNs topic/bundle id is not configured.")

        aps = {
            "alert": {
                "title": title,
                "body": body,
            },
            "sound": "default",
        }
        if badge_count is not None:
            aps["badge"] = badge_count

        payload = {
            "aps": aps,
            **_json_safe_data(data),
        }
        headers = {
            "authorization": f"bearer {_apns_auth_token()}",
            "apns-topic": topic,
            "apns-push-type": "alert",
            "apns-priority": "10",
        }
        host = (
            APNS_SANDBOX_HOST
            if device.environment == PushDevice.ENVIRONMENT_SANDBOX
            else APNS_PRODUCTION_HOST
        )
        url = f"{host}/3/device/{device.token}"

        import httpx

        with httpx.Client(http2=True, timeout=APNS_TIMEOUT_SECONDS) as client:
            response = client.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            return

        reason = _apns_error_reason(response)
        message = f"APNs {response.status_code}: {reason}"
        if response.status_code == 410 or reason in {
            "BadDeviceToken",
            "DeviceTokenNotForTopic",
            "Unregistered",
        }:
            raise APNsPermanentDeviceError(message)
        raise APNsError(message)


def _apns_auth_token() -> str:
    global _cached_auth_token, _cached_auth_token_created_at

    now = time.time()
    if (
        _cached_auth_token
        and now - _cached_auth_token_created_at < APNS_TOKEN_TTL_SECONDS
    ):
        return _cached_auth_token

    payload = {
        "iss": settings.APNS_TEAM_ID,
        "iat": int(now),
    }
    headers = {
        "alg": "ES256",
        "kid": settings.APNS_KEY_ID,
    }
    _cached_auth_token = jwt.encode(
        payload,
        _apns_private_key(),
        algorithm="ES256",
        headers=headers,
    )
    _cached_auth_token_created_at = now
    return _cached_auth_token


def _apns_private_key() -> str:
    if settings.APNS_AUTH_KEY:
        return settings.APNS_AUTH_KEY.replace("\\n", "\n")

    with open(settings.APNS_AUTH_KEY_PATH) as key_file:
        return key_file.read()


def _apns_error_reason(response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:200]
    return payload.get("reason") or response.text[:200]


def _json_safe_data(data: dict) -> dict:
    safe = {}
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            safe[key] = value
        else:
            safe[key] = str(value)
    return safe


def _badge_count_for_event(event: PushNotificationEvent) -> int | None:
    title_slug = (event.data or {}).get("title_slug")
    if not title_slug:
        return None

    from apps.core.lobby_notifications import get_title_lobby_badge_count_by_slug

    return get_title_lobby_badge_count_by_slug(event.user_id, title_slug)


def _user_id_for_side(game, side: str) -> int | None:
    if side == "side_a":
        return game.player_a_user_id
    if side == "side_b":
        return game.player_b_user_id
    return None


def _opponent_name_for_side(game, side: str) -> str:
    opponent = game.side_b if side == "side_a" else game.side_a
    return opponent.owner_name if not opponent.is_ai_deck else opponent.name

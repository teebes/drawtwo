#!/usr/bin/env bash
set -euo pipefail

choose_default_simulator() {
  local candidates=(
    "iPhone 17 Pro"
    "iPhone 16 Pro"
    "iPhone 15 Pro"
  )
  local devices

  devices="$(xcrun simctl list devices available 2>/dev/null || true)"

  for candidate in "${candidates[@]}"; do
    if grep -Eq "^[[:space:]]+$candidate \\(" <<<"$devices"; then
      printf '%s\n' "$candidate"
      return
    fi
  done

  printf '%s\n' "iPhone 16 Pro"
}

resolve_simulator_udid() {
  local simulator_name="$1"
  local devices
  local line

  devices="$(xcrun simctl list devices available 2>/dev/null || true)"
  line="$(grep -E "^[[:space:]]+$simulator_name \\(" <<<"$devices" | head -n 1 || true)"

  if [[ -z "$line" ]]; then
    return
  fi

  sed -E 's/.*\(([0-9A-F-]+)\).*/\1/' <<<"$line"
}

SIMULATOR_NAME="${SIMULATOR_NAME:-$(choose_default_simulator)}"
SIMULATOR_UDID="${SIMULATOR_UDID:-$(resolve_simulator_udid "$SIMULATOR_NAME")}"
BACKEND_BASE_URL="${ARCHETYPE_BACKEND_BASE_URL:-http://127.0.0.1:8002}"
INITIAL_DASHBOARD_SECTION="${ARCHETYPE_INITIAL_DASHBOARD_SECTION:-}"
INITIAL_COLLECTION_CARD_SLUG="${ARCHETYPE_INITIAL_COLLECTION_CARD_SLUG:-}"
INITIAL_DECK_CARD_SLUG="${ARCHETYPE_INITIAL_DECK_CARD_SLUG:-}"
INITIAL_DECK_ID="${ARCHETYPE_INITIAL_DECK_ID:-}"
INITIAL_GAME_ID="${ARCHETYPE_INITIAL_GAME_ID:-}"
INITIAL_GAME_OVERLAY="${ARCHETYPE_INITIAL_GAME_OVERLAY:-}"
INITIAL_GAME_COMMAND="${ARCHETYPE_INITIAL_GAME_COMMAND:-}"
INITIAL_PROFILE_MENU="${ARCHETYPE_INITIAL_PROFILE_MENU:-}"
INITIAL_PROFILE_EDIT="${ARCHETYPE_INITIAL_PROFILE_EDIT:-}"
INITIAL_PROFILE_USERNAME="${ARCHETYPE_INITIAL_PROFILE_USERNAME:-}"
INITIAL_PROFILE_SAVE="${ARCHETYPE_INITIAL_PROFILE_SAVE:-}"
INITIAL_THEME="${ARCHETYPE_INITIAL_THEME:-}"
INITIAL_LOGIN_MODE="${ARCHETYPE_INITIAL_LOGIN_MODE:-}"
QUEUE_ELAPSED_SECONDS="${ARCHETYPE_QUEUE_ELAPSED_SECONDS:-}"
VISUAL_CAPTURE="${ARCHETYPE_VISUAL_CAPTURE:-0}"
CAPTURE_STATE="${ARCHETYPE_CAPTURE_STATE:-0}"
EXPECTED_CAPTURE_STATE="${ARCHETYPE_EXPECTED_CAPTURE_STATE:-}"
EXPECTED_CAPTURE_DETAIL="${ARCHETYPE_EXPECTED_CAPTURE_DETAIL:-}"
SHOW_LOCAL_ACCOUNT_SHORTCUT="${ARCHETYPE_SHOW_LOCAL_ACCOUNT_SHORTCUT:-0}"
SHOW_MANUAL_LOGIN_LINK_SHORTCUT="${ARCHETYPE_SHOW_MANUAL_LOGIN_LINK_SHORTCUT:-0}"
SCREENSHOT_PATH="${ARCHETYPE_SCREENSHOT_PATH:-}"
SCREENSHOT_DELAY="${ARCHETYPE_SCREENSHOT_DELAY:-4}"
AUTO_LOGIN="${ARCHETYPE_AUTO_LOGIN:-1}"
CLEAR_SESSION="${ARCHETYPE_CLEAR_SESSION:-0}"
SEED_QUEUE_LADDER="${ARCHETYPE_SEED_QUEUE_LADDER:-daily}"
SEED_QUEUE_AGE_SECONDS="${ARCHETYPE_SEED_QUEUE_AGE_SECONDS:-0}"
SEED_GAME_AGE_SECONDS="${ARCHETYPE_SEED_GAME_AGE_SECONDS:-0}"
SKIP_STACK="${ARCHETYPE_SKIP_STACK:-0}"
SKIP_BUILD="${ARCHETYPE_SKIP_BUILD:-0}"
SKIP_INSTALL="${ARCHETYPE_SKIP_INSTALL:-0}"
LOCAL_UI_LOCK_DIR="${ARCHETYPE_LOCAL_UI_LOCK_DIR:-${TMPDIR:-/tmp}/archetype-run-ios-local-ui.lock}"
DISABLE_LOCAL_UI_LOCK="${ARCHETYPE_DISABLE_LOCAL_UI_LOCK:-0}"
PROJECT_PATH="ios/Archetype/Archetype.xcodeproj"
SCHEME="Archetype"
BUNDLE_ID="com.morelsoft.drawtwo.dev"
DERIVED_DATA_PATH="build/ios-simulator"
APP_PATH="$DERIVED_DATA_PATH/Build/Products/Debug-iphonesimulator/Archetype.app"

truthy() {
  [[ "$1" == "1" || "$1" == "true" || "$1" == "yes" || "$1" == "on" ]]
}

LOCAL_UI_LOCK_HELD=0

release_local_ui_lock() {
  if [[ "$LOCAL_UI_LOCK_HELD" == "1" ]]; then
    rm -rf "$LOCAL_UI_LOCK_DIR"
  fi
}

acquire_local_ui_lock() {
  if truthy "$DISABLE_LOCAL_UI_LOCK"; then
    return
  fi

  local waited=0
  local lock_pid

  while ! mkdir "$LOCAL_UI_LOCK_DIR" 2>/dev/null; do
    lock_pid="$(cat "$LOCAL_UI_LOCK_DIR/pid" 2>/dev/null || true)"
    if [[ -n "$lock_pid" ]] && ! kill -0 "$lock_pid" 2>/dev/null; then
      rm -rf "$LOCAL_UI_LOCK_DIR"
      continue
    fi

    if [[ "$waited" == "0" ]]; then
      echo "Waiting for local UI simulator lock: $LOCAL_UI_LOCK_DIR"
    fi
    waited=$((waited + 1))
    sleep 1
  done

  LOCAL_UI_LOCK_HELD=1
  printf '%s\n' "$$" > "$LOCAL_UI_LOCK_DIR/pid"
  trap release_local_ui_lock EXIT INT TERM
}

if [[ -z "$SIMULATOR_UDID" ]]; then
  echo "Could not find an available simulator named '$SIMULATOR_NAME'." >&2
  echo "Set SIMULATOR_NAME to an installed device or SIMULATOR_UDID to a device UDID." >&2
  exit 1
fi

acquire_local_ui_lock

if truthy "$SKIP_STACK"; then
  echo "Using existing local DrawTwo stack."
else
  echo "Starting local DrawTwo stack..."
  docker compose up -d
  docker compose exec backend python manage.py migrate
  docker compose exec backend python manage.py seed_archetype_dev \
    --queue-ladder "$SEED_QUEUE_LADDER" \
    --queue-age-seconds "$SEED_QUEUE_AGE_SECONDS" \
    --game-age-seconds "$SEED_GAME_AGE_SECONDS"
fi

resolve_latest_game_id() {
  local phase="${1:-main}"
  docker compose exec -T backend python manage.py shell -c \
    "from django.contrib.auth import get_user_model; from apps.gameplay.models import Game; user = get_user_model().objects.get(email='ios@devdata.local'); games = Game.objects.for_user(user).filter(type=Game.GAME_TYPE_PVE, status=Game.GAME_STATUS_IN_PROGRESS).order_by('-created_at'); game = next((g for g in games if (g.state or {}).get('phase') == '$phase'), None); print(game.id if game else '')" \
    | tr -d '\r' \
    | tail -n 1
}

resolve_latest_ended_ranked_game_id() {
  docker compose exec -T backend python manage.py shell -c \
    "from django.contrib.auth import get_user_model; from apps.gameplay.models import Game; user = get_user_model().objects.get(email='ios@devdata.local'); game = Game.objects.for_user(user).filter(type=Game.GAME_TYPE_RANKED, status=Game.GAME_STATUS_ENDED).order_by('-created_at').first(); print(game.id if game else '')" \
    | tr -d '\r' \
    | tail -n 1
}

if [[ "$INITIAL_GAME_ID" == "latest" || "$INITIAL_GAME_ID" == "active" ]]; then
  INITIAL_GAME_ID="$(resolve_latest_game_id)"
elif [[ "$INITIAL_GAME_ID" == "latest_mulligan" || "$INITIAL_GAME_ID" == "latest-mulligan" || "$INITIAL_GAME_ID" == "mulligan" ]]; then
  INITIAL_GAME_ID="$(resolve_latest_game_id mulligan)"
elif [[ "$INITIAL_GAME_ID" == "latest_ended_ranked" || "$INITIAL_GAME_ID" == "latest-ended-ranked" || "$INITIAL_GAME_ID" == "ended_ranked" || "$INITIAL_GAME_ID" == "ended-ranked" ]]; then
  INITIAL_GAME_ID="$(resolve_latest_ended_ranked_game_id)"
fi

if [[ -z "$INITIAL_GAME_ID" && ( -n "$INITIAL_GAME_OVERLAY" || -n "$INITIAL_GAME_COMMAND" ) ]]; then
  INITIAL_GAME_ID="$(resolve_latest_game_id)"
fi

if [[ -z "$INITIAL_GAME_ID" && ( -n "$INITIAL_GAME_OVERLAY" || -n "$INITIAL_GAME_COMMAND" ) ]]; then
  echo "No seeded active game was found for the requested game launch." >&2
  exit 1
fi

if [[ -n "$INITIAL_GAME_ID" ]]; then
  echo "Launching seeded game: $INITIAL_GAME_ID"
fi

echo "Booting simulator: $SIMULATOR_NAME ($SIMULATOR_UDID)"
xcrun simctl boot "$SIMULATOR_UDID" >/dev/null 2>&1 || true
xcrun simctl bootstatus "$SIMULATOR_UDID" -b
open -a Simulator

if truthy "$SKIP_BUILD"; then
  echo "Using existing simulator build at $APP_PATH"
else
  echo "Building Archetype for simulator..."
  xcodebuild \
    -project "$PROJECT_PATH" \
    -scheme "$SCHEME" \
    -destination "platform=iOS Simulator,id=$SIMULATOR_UDID" \
    -derivedDataPath "$DERIVED_DATA_PATH" \
    CODE_SIGNING_ALLOWED=NO \
    build
fi

if truthy "$SKIP_INSTALL"; then
  echo "Using already installed $BUNDLE_ID"
else
  echo "Installing $APP_PATH"
  xcrun simctl install "$SIMULATOR_UDID" "$APP_PATH"
fi

capture_state_enabled() {
  truthy "$CAPTURE_STATE" || [[ -n "$EXPECTED_CAPTURE_STATE" || -n "$EXPECTED_CAPTURE_DETAIL" ]]
}

if capture_state_enabled; then
  if app_data_container="$(xcrun simctl get_app_container "$SIMULATOR_UDID" "$BUNDLE_ID" data 2>/dev/null)"; then
    rm -f "$app_data_container/Documents/archetype_capture_state.json"
  fi
fi

echo "Launching $BUNDLE_ID against $BACKEND_BASE_URL"
launch_env=(
  "SIMCTL_CHILD_ARCHETYPE_BACKEND_BASE_URL=$BACKEND_BASE_URL"
  "SIMCTL_CHILD_ARCHETYPE_AUTO_LOGIN=$AUTO_LOGIN"
)

if truthy "$CLEAR_SESSION"; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_CLEAR_SESSION=1")
fi

if truthy "$SHOW_LOCAL_ACCOUNT_SHORTCUT"; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_SHOW_LOCAL_ACCOUNT_SHORTCUT=1")
fi

if truthy "$SHOW_MANUAL_LOGIN_LINK_SHORTCUT"; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_SHOW_MANUAL_LOGIN_LINK_SHORTCUT=1")
fi

if [[ -n "$INITIAL_DASHBOARD_SECTION" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_DASHBOARD_SECTION=$INITIAL_DASHBOARD_SECTION")
fi

if [[ -n "$INITIAL_COLLECTION_CARD_SLUG" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_COLLECTION_CARD_SLUG=$INITIAL_COLLECTION_CARD_SLUG")
fi

if [[ -n "$INITIAL_DECK_CARD_SLUG" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_DECK_CARD_SLUG=$INITIAL_DECK_CARD_SLUG")
fi

if [[ -n "$INITIAL_DECK_ID" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_DECK_ID=$INITIAL_DECK_ID")
fi

if [[ -n "$INITIAL_GAME_ID" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_GAME_ID=$INITIAL_GAME_ID")
fi

if [[ -n "$INITIAL_GAME_OVERLAY" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_GAME_OVERLAY=$INITIAL_GAME_OVERLAY")
fi

if [[ -n "$INITIAL_GAME_COMMAND" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_GAME_COMMAND=$INITIAL_GAME_COMMAND")
fi

if [[ -n "$INITIAL_PROFILE_MENU" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_PROFILE_MENU=$INITIAL_PROFILE_MENU")
fi

if [[ -n "$INITIAL_PROFILE_EDIT" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_PROFILE_EDIT=$INITIAL_PROFILE_EDIT")
fi

if [[ -n "$INITIAL_PROFILE_USERNAME" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_PROFILE_USERNAME=$INITIAL_PROFILE_USERNAME")
fi

if [[ -n "$INITIAL_PROFILE_SAVE" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_PROFILE_SAVE=$INITIAL_PROFILE_SAVE")
fi

if [[ -n "$INITIAL_THEME" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_THEME=$INITIAL_THEME")
fi

if [[ -n "$INITIAL_LOGIN_MODE" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_INITIAL_LOGIN_MODE=$INITIAL_LOGIN_MODE")
fi

if [[ -n "$QUEUE_ELAPSED_SECONDS" ]]; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_QUEUE_ELAPSED_SECONDS=$QUEUE_ELAPSED_SECONDS")
fi

if truthy "$VISUAL_CAPTURE"; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_VISUAL_CAPTURE=1")
fi

if capture_state_enabled; then
  launch_env+=("SIMCTL_CHILD_ARCHETYPE_CAPTURE_STATE=1")
fi

env "${launch_env[@]}" xcrun simctl launch --terminate-running-process "$SIMULATOR_UDID" "$BUNDLE_ID"

if [[ -n "$SCREENSHOT_PATH" ]]; then
  sleep "$SCREENSHOT_DELAY"
  xcrun simctl io "$SIMULATOR_UDID" screenshot "$SCREENSHOT_PATH"
  echo "Saved simulator screenshot to $SCREENSHOT_PATH"
fi

if [[ -n "$EXPECTED_CAPTURE_STATE" || -n "$EXPECTED_CAPTURE_DETAIL" ]]; then
  app_data_container="$(xcrun simctl get_app_container "$SIMULATOR_UDID" "$BUNDLE_ID" data)"
  capture_state_file="$app_data_container/Documents/archetype_capture_state.json"
  python3 - "$EXPECTED_CAPTURE_STATE" "$EXPECTED_CAPTURE_DETAIL" "$capture_state_file" <<'PY'
import json
import sys
import time
from pathlib import Path

expected = {item.strip() for item in sys.argv[1].split(",") if item.strip()}
expected_details = {}
for item in sys.argv[2].split(","):
    item = item.strip()
    if not item:
        continue
    if "=" not in item:
        print(f"Invalid capture detail expectation {item!r}; expected key=value.", file=sys.stderr)
        sys.exit(2)
    key, value = item.split("=", 1)
    expected_details[key.strip()] = value.strip()

state_path = Path(sys.argv[3])
payload = None

for _ in range(20):
    if state_path.exists():
        try:
            payload = json.loads(state_path.read_text())
            break
        except json.JSONDecodeError:
            pass
    time.sleep(0.25)

if not payload:
    print(f"Missing iOS capture state file: {state_path}", file=sys.stderr)
    sys.exit(1)

screen = payload.get("screen")
if expected and screen not in expected:
    expected_text = ", ".join(sorted(expected))
    print(
        f"Unexpected iOS capture state: {screen!r}; expected one of: {expected_text}. "
        f"State file: {state_path}",
        file=sys.stderr,
    )
    sys.exit(1)

for key, expected_value in expected_details.items():
    actual_value = str(payload.get(key, ""))
    if actual_value != expected_value:
        print(
            f"Unexpected iOS capture detail {key}: {actual_value!r}; "
            f"expected {expected_value!r}. State file: {state_path}",
            file=sys.stderr,
        )
        sys.exit(1)

details_text = ", ".join(f"{key}={value}" for key, value in expected_details.items())
if details_text:
    print(f"Verified iOS capture state: {screen} ({details_text})")
else:
    print(f"Verified iOS capture state: {screen}")
PY
fi

echo "Archetype is running with seeded local account ios@devdata.local."

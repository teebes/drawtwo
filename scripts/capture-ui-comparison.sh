#!/usr/bin/env bash
set -euo pipefail

WEB_DIR="${ARCHETYPE_WEB_SCREENSHOT_DIR:-/tmp/archetype-web-ui}"
IOS_RAW_DIR="${ARCHETYPE_IOS_RAW_SCREENSHOT_DIR:-/tmp/archetype-ios-ui-raw}"
IOS_DIR="${ARCHETYPE_IOS_SCREENSHOT_DIR:-/tmp/archetype-ios-ui}"
COMPARISON_DIR="${ARCHETYPE_UI_COMPARISON_DIR:-/tmp/archetype-ui-comparison}"
IOS_DISPLAY_WIDTH="${ARCHETYPE_IOS_DISPLAY_WIDTH:-${ARCHETYPE_WEB_VIEWPORT_WIDTH:-390}}"
SEED_QUEUE_LADDER="${ARCHETYPE_SEED_QUEUE_LADDER:-daily}"
SEED_QUEUE_AGE_SECONDS="${ARCHETYPE_SEED_QUEUE_AGE_SECONDS:-0}"
SEED_GAME_AGE_SECONDS="${ARCHETYPE_SEED_GAME_AGE_SECONDS:--3600}"
IOS_RANKED_QUEUE_SEED_AGE_SECONDS="${ARCHETYPE_IOS_RANKED_QUEUE_SEED_AGE_SECONDS:-${ARCHETYPE_RANKED_QUEUE_SEED_AGE_SECONDS:-0}}"
IOS_RANKED_QUEUE_ELAPSED_SECONDS="${ARCHETYPE_IOS_RANKED_QUEUE_ELAPSED_SECONDS:-${ARCHETYPE_RANKED_QUEUE_ELAPSED_SECONDS:-3}}"
WEB_QUEUE_CAPTURE_AGE_SECONDS="${ARCHETYPE_WEB_QUEUE_CAPTURE_AGE_SECONDS:-0}"
CAPTURE_NAMES="${ARCHETYPE_CAPTURE_NAMES:-}"

WEB_EXPECTED_CAPTURES=(
  login
  login-signup
  dashboard
  dashboard-how-to
  profile-menu
  how-to
  games
  collection
  collection-card-detail
  deck
  deck-card-detail
  new-game
  new-game-ai
  leaderboard
  friends
  profile
  profile-edit
  ranked-queue-daily
  ranked-queue-rapid
  game-over-ranked
  game-mulligan
  game-board
  game-own-hero
  game-opponent-hero
  game-own-creature
  game-opponent-creature
  game-menu
  game-updates
  game-hand-card
  game-hand-creature
  game-placement
  game-targeting-spell
  game-targeting-attack
  game-command-zap-board
  game-command-play-creature
  game-command-attack
  game-command-hero-power
  game-command-end-turn
)

IOS_EXPECTED_CAPTURES=(
  login
  login-signup
  login-confirm
  dashboard
  dashboard-how-to
  profile-menu
  how-to
  games
  collection
  collection-card-detail
  deck
  deck-card-detail
  new-game
  new-game-ai
  leaderboard
  friends
  profile
  profile-edit
  ranked-queue-daily
  ranked-queue-rapid
  game-over-ranked
  game-mulligan
  game-board
  game-own-hero
  game-opponent-hero
  game-own-creature
  game-opponent-creature
  game-menu
  game-updates
  game-hand-card
  game-hand-creature
  game-placement
  game-targeting-spell
  game-targeting-attack
  game-command-zap-board
  game-command-play-creature
  game-command-attack
  game-command-hero-power
  game-command-end-turn
)

should_capture() {
  local target="$1"
  local normalized_names

  if [[ -z "$CAPTURE_NAMES" ]]; then
    return 0
  fi

  normalized_names="${CAPTURE_NAMES//,/ }"
  for name in $normalized_names; do
    if [[ "$name" == "$target" ]]; then
      return 0
    fi
  done

  return 1
}

WEB_CAPTURES_TO_VERIFY=()
for name in "${WEB_EXPECTED_CAPTURES[@]}"; do
  if should_capture "$name"; then
    WEB_CAPTURES_TO_VERIFY+=("$name")
  fi
done

IOS_CAPTURES_TO_VERIFY=()
for name in "${IOS_EXPECTED_CAPTURES[@]}"; do
  if should_capture "$name"; then
    IOS_CAPTURES_TO_VERIFY+=("$name")
  fi
done

verify_capture_dir() {
  local label="$1"
  local dir="$2"
  shift 2
  local expected_captures=("$@")
  local failures=0

  for name in "${expected_captures[@]}"; do
    local image="$dir/$name.png"

    if [[ ! -s "$image" ]]; then
      echo "Missing or empty $label capture: $image" >&2
      failures=1
      continue
    fi

    if command -v sips >/dev/null 2>&1; then
      local width
      local height
      width="$(
        sips -g pixelWidth "$image" 2>/dev/null \
          | awk '/pixelWidth/ { print $2 }'
      )"
      height="$(
        sips -g pixelHeight "$image" 2>/dev/null \
          | awk '/pixelHeight/ { print $2 }'
      )"

      if [[ -z "$width" || -z "$height" || "$width" -le 0 || "$height" -le 0 ]]; then
        echo "Invalid $label capture dimensions: $image" >&2
        failures=1
      fi
    fi
  done

  if [[ "$failures" -ne 0 ]]; then
    exit 1
  fi
}

if [[ "${ARCHETYPE_SKIP_STACK:-0}" != "0" && "${ARCHETYPE_RESEED_BEFORE_WEB_CAPTURE:-1}" != "0" ]]; then
  echo "Reseeding local Archetype data before web capture..."
  docker compose exec -T backend \
    python manage.py seed_archetype_dev \
      --queue-ladder "$SEED_QUEUE_LADDER" \
      --queue-age-seconds "$SEED_QUEUE_AGE_SECONDS" \
      --game-age-seconds "$SEED_GAME_AGE_SECONDS"
fi

echo "Capturing web reference screens into $WEB_DIR..."
ARCHETYPE_WEB_SCREENSHOT_DIR="$WEB_DIR" \
ARCHETYPE_CAPTURE_NAMES="$CAPTURE_NAMES" \
ARCHETYPE_SEED_GAME_AGE_SECONDS="$SEED_GAME_AGE_SECONDS" \
ARCHETYPE_QUEUE_CAPTURE_AGE_SECONDS="$WEB_QUEUE_CAPTURE_AGE_SECONDS" \
scripts/capture-web-ui.sh
verify_capture_dir "web" "$WEB_DIR" "${WEB_CAPTURES_TO_VERIFY[@]}"

if [[ "${ARCHETYPE_RESEED_BEFORE_IOS_CAPTURE:-1}" != "0" ]]; then
  echo "Reseeding local Archetype data before iOS capture..."
  docker compose exec -T backend \
    python manage.py seed_archetype_dev \
      --queue-ladder "$SEED_QUEUE_LADDER" \
      --queue-age-seconds "$SEED_QUEUE_AGE_SECONDS" \
      --game-age-seconds "$SEED_GAME_AGE_SECONDS"
fi

echo "Capturing iOS screens from the matching deterministic local seed into $IOS_RAW_DIR..."
ARCHETYPE_IOS_SCREENSHOT_DIR="$IOS_RAW_DIR" \
ARCHETYPE_CAPTURE_NAMES="$CAPTURE_NAMES" \
ARCHETYPE_SEED_GAME_AGE_SECONDS="$SEED_GAME_AGE_SECONDS" \
ARCHETYPE_RANKED_QUEUE_SEED_AGE_SECONDS="$IOS_RANKED_QUEUE_SEED_AGE_SECONDS" \
ARCHETYPE_RANKED_QUEUE_ELAPSED_SECONDS="$IOS_RANKED_QUEUE_ELAPSED_SECONDS" \
ARCHETYPE_SKIP_STACK=1 \
scripts/capture-ios-ui.sh
verify_capture_dir "raw iOS" "$IOS_RAW_DIR" "${IOS_CAPTURES_TO_VERIFY[@]}"

rm -rf "$IOS_DIR"
mkdir -p "$IOS_DIR"

for image in "$IOS_RAW_DIR"/*.png; do
  [[ -e "$image" ]] || continue

  output="$IOS_DIR/$(basename "$image")"
  cp "$image" "$output"

  if command -v sips >/dev/null 2>&1; then
    width="$(
      sips -g pixelWidth "$image" 2>/dev/null \
        | awk '/pixelWidth/ { print $2 }'
    )"
    height="$(
      sips -g pixelHeight "$image" 2>/dev/null \
        | awk '/pixelHeight/ { print $2 }'
    )"

    if [[ -n "$width" && -n "$height" && "$width" -gt 0 ]]; then
      display_height=$(( (height * IOS_DISPLAY_WIDTH + width / 2) / width ))
      sips -z "$display_height" "$IOS_DISPLAY_WIDTH" "$output" >/dev/null 2>&1
    fi
  fi
done

verify_capture_dir "scaled iOS" "$IOS_DIR" "${IOS_CAPTURES_TO_VERIFY[@]}"

echo "Building side-by-side comparison gallery..."
ARCHETYPE_WEB_SCREENSHOT_DIR="$WEB_DIR" \
ARCHETYPE_IOS_SCREENSHOT_DIR="$IOS_DIR" \
ARCHETYPE_UI_COMPARISON_DIR="$COMPARISON_DIR" \
scripts/build-ui-comparison-gallery.sh

echo "Web captures: $WEB_DIR"
echo "Raw iOS captures: $IOS_RAW_DIR"
echo "Scaled iOS captures: $IOS_DIR"
echo "Comparison gallery: $COMPARISON_DIR/index.html"

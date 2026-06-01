#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${ARCHETYPE_IOS_SCREENSHOT_DIR:-${ARCHETYPE_SCREENSHOT_DIR:-/tmp/archetype-ios-ui}}"
SCREENSHOT_DELAY="${ARCHETYPE_SCREENSHOT_DELAY:-6}"
GAME_SCREENSHOT_DELAY="${ARCHETYPE_GAME_SCREENSHOT_DELAY:-8}"
GAME_HERO_SCREENSHOT_DELAY="${ARCHETYPE_GAME_HERO_SCREENSHOT_DELAY:-15}"
RANKED_QUEUE_SCREENSHOT_DELAY="${ARCHETYPE_RANKED_QUEUE_SCREENSHOT_DELAY:-6}"
RANKED_QUEUE_SEED_AGE_SECONDS="${ARCHETYPE_RANKED_QUEUE_SEED_AGE_SECONDS:-0}"
RANKED_QUEUE_ELAPSED_SECONDS="${ARCHETYPE_RANKED_QUEUE_ELAPSED_SECONDS:-3}"
SEED_GAME_AGE_SECONDS="${ARCHETYPE_SEED_GAME_AGE_SECONDS:-0}"
VISUAL_CAPTURE="${ARCHETYPE_VISUAL_CAPTURE:-1}"
CAPTURE_NAMES="${ARCHETYPE_CAPTURE_NAMES:-}"
CAPTURE_HAS_RUN=0
mkdir -p "$OUT_DIR"
find "$OUT_DIR" -maxdepth 1 -type f \( -name '*.png' -o -name 'index.html' \) -delete

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

expected_state_for_capture() {
  case "$1" in
    dashboard-how-to)
      printf '%s\n' "dashboard"
      ;;
    game-own-creature)
      printf '%s\n' "game-own-creature,game-targeting-attack"
      ;;
    game-command-zap-board)
      printf '%s\n' "game-board"
      ;;
    game-command-play-creature)
      printf '%s\n' "game-updates"
      ;;
    game-command-attack)
      printf '%s\n' "game-updates"
      ;;
    game-command-hero-power)
      printf '%s\n' "game-updates"
      ;;
    game-command-end-turn)
      printf '%s\n' "game-updates"
      ;;
    *)
      printf '%s\n' "$1"
      ;;
  esac
}

expected_detail_for_capture() {
  case "$1" in
    game-command-zap-board)
      printf '%s\n' "latest_update_type=update_damage"
      ;;
    game-command-play-creature)
      printf '%s\n' "latest_update_type=update_play_card"
      ;;
    game-command-attack)
      printf '%s\n' "latest_update_type=update_damage"
      ;;
    game-command-hero-power)
      printf '%s\n' "latest_update_type=update_draw_card"
      ;;
    game-command-end-turn)
      printf '%s\n' "has_end_turn_update=1"
      ;;
    *)
      printf '%s\n' ""
      ;;
  esac
}

run_capture() {
  local name="$1"
  local expected_state
  local expected_detail
  local launch_args
  shift

  if ! should_capture "$name"; then
    return
  fi

  launch_args=("$@")
  if [[ "$CAPTURE_HAS_RUN" == "0" ]]; then
    local prepared_args=()
    local arg
    for arg in "${launch_args[@]}"; do
      case "$arg" in
        ARCHETYPE_SKIP_STACK=*|ARCHETYPE_SKIP_BUILD=*|ARCHETYPE_SKIP_INSTALL=*)
          ;;
        *)
          prepared_args+=("$arg")
          ;;
      esac
    done
    if [[ "${#prepared_args[@]}" -gt 0 ]]; then
      launch_args=("${prepared_args[@]}")
    else
      launch_args=()
    fi
  fi

  expected_state="$(expected_state_for_capture "$name")"
  expected_detail="$(expected_detail_for_capture "$name")"
  echo "Capturing $name..."
  if [[ "${#launch_args[@]}" -gt 0 ]]; then
    env \
      ARCHETYPE_SCREENSHOT_PATH="$OUT_DIR/$name.png" \
      ARCHETYPE_SCREENSHOT_DELAY="$SCREENSHOT_DELAY" \
      ARCHETYPE_SEED_GAME_AGE_SECONDS="$SEED_GAME_AGE_SECONDS" \
      ARCHETYPE_VISUAL_CAPTURE="$VISUAL_CAPTURE" \
      ARCHETYPE_CAPTURE_STATE=1 \
      ARCHETYPE_EXPECTED_CAPTURE_STATE="$expected_state" \
      ARCHETYPE_EXPECTED_CAPTURE_DETAIL="$expected_detail" \
      "${launch_args[@]}" \
      scripts/run-ios-local-ui.sh
  else
    env \
      ARCHETYPE_SCREENSHOT_PATH="$OUT_DIR/$name.png" \
      ARCHETYPE_SCREENSHOT_DELAY="$SCREENSHOT_DELAY" \
      ARCHETYPE_SEED_GAME_AGE_SECONDS="$SEED_GAME_AGE_SECONDS" \
      ARCHETYPE_VISUAL_CAPTURE="$VISUAL_CAPTURE" \
      ARCHETYPE_CAPTURE_STATE=1 \
      ARCHETYPE_EXPECTED_CAPTURE_STATE="$expected_state" \
      ARCHETYPE_EXPECTED_CAPTURE_DETAIL="$expected_detail" \
      scripts/run-ios-local-ui.sh
  fi

  CAPTURE_HAS_RUN=1
}

run_fast_capture() {
  local name="$1"
  shift

  run_capture "$name" \
    ARCHETYPE_SKIP_STACK=1 \
    ARCHETYPE_SKIP_BUILD=1 \
    ARCHETYPE_SKIP_INSTALL=1 \
    "$@"
}

run_capture "login" \
  ARCHETYPE_AUTO_LOGIN=0 \
  ARCHETYPE_CLEAR_SESSION=1
run_fast_capture "login-signup" \
  ARCHETYPE_AUTO_LOGIN=0 \
  ARCHETYPE_CLEAR_SESSION=1 \
  ARCHETYPE_INITIAL_LOGIN_MODE=signup
run_fast_capture "login-confirm" \
  ARCHETYPE_AUTO_LOGIN=0 \
  ARCHETYPE_CLEAR_SESSION=1 \
  ARCHETYPE_INITIAL_LOGIN_MODE=confirm
run_fast_capture "dashboard"
run_fast_capture "dashboard-how-to" ARCHETYPE_INITIAL_DASHBOARD_SECTION=scroll_how_to
run_fast_capture "profile-menu" ARCHETYPE_INITIAL_PROFILE_MENU=1
run_fast_capture "how-to" ARCHETYPE_INITIAL_DASHBOARD_SECTION=how_to
run_fast_capture "games" ARCHETYPE_INITIAL_DASHBOARD_SECTION=games
run_fast_capture "collection" ARCHETYPE_INITIAL_DASHBOARD_SECTION=collection
run_fast_capture "collection-card-detail" \
  ARCHETYPE_INITIAL_DASHBOARD_SECTION=collection \
  ARCHETYPE_INITIAL_COLLECTION_CARD_SLUG=first
run_fast_capture "deck" ARCHETYPE_INITIAL_DASHBOARD_SECTION=deck
run_fast_capture "deck-card-detail" \
  ARCHETYPE_INITIAL_DASHBOARD_SECTION=deck \
  ARCHETYPE_INITIAL_DECK_CARD_SLUG=first
run_fast_capture "new-game" ARCHETYPE_INITIAL_DASHBOARD_SECTION=new_game
run_fast_capture "new-game-ai" ARCHETYPE_INITIAL_DASHBOARD_SECTION=new_game_ai
run_fast_capture "leaderboard" \
  ARCHETYPE_INITIAL_DASHBOARD_SECTION=leaderboard \
  ARCHETYPE_SCREENSHOT_DELAY="${ARCHETYPE_LEADERBOARD_SCREENSHOT_DELAY:-8}"
run_fast_capture "friends" ARCHETYPE_INITIAL_DASHBOARD_SECTION=friends
run_fast_capture "profile" ARCHETYPE_INITIAL_DASHBOARD_SECTION=profile
run_fast_capture "profile-edit" \
  ARCHETYPE_INITIAL_DASHBOARD_SECTION=profile \
  ARCHETYPE_INITIAL_PROFILE_EDIT=1
run_capture "ranked-queue-daily" \
  ARCHETYPE_SKIP_STACK=0 \
  ARCHETYPE_SKIP_BUILD=1 \
  ARCHETYPE_SKIP_INSTALL=1 \
  ARCHETYPE_SEED_QUEUE_LADDER=daily \
  ARCHETYPE_SEED_QUEUE_AGE_SECONDS="$RANKED_QUEUE_SEED_AGE_SECONDS" \
  ARCHETYPE_INITIAL_DASHBOARD_SECTION=ranked_queue_daily \
  ARCHETYPE_SCREENSHOT_DELAY="$RANKED_QUEUE_SCREENSHOT_DELAY"
run_fast_capture "game-over-ranked" \
  ARCHETYPE_INITIAL_GAME_ID=latest_ended_ranked \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_SCREENSHOT_DELAY"
run_fast_capture "game-mulligan" \
  ARCHETYPE_INITIAL_GAME_ID=latest_mulligan \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_SCREENSHOT_DELAY"
run_fast_capture "game-board" \
  ARCHETYPE_INITIAL_GAME_ID=latest \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_SCREENSHOT_DELAY"
run_fast_capture "game-own-hero" \
  ARCHETYPE_INITIAL_GAME_OVERLAY=own_hero \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_HERO_SCREENSHOT_DELAY"
run_fast_capture "game-opponent-hero" \
  ARCHETYPE_INITIAL_GAME_OVERLAY=opponent_hero \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_HERO_SCREENSHOT_DELAY"
run_fast_capture "game-own-creature" \
  ARCHETYPE_INITIAL_GAME_OVERLAY=own_creature \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_SCREENSHOT_DELAY"
run_fast_capture "game-opponent-creature" \
  ARCHETYPE_INITIAL_GAME_OVERLAY=opponent_creature \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_SCREENSHOT_DELAY"
run_fast_capture "game-menu" \
  ARCHETYPE_INITIAL_GAME_OVERLAY=menu \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_SCREENSHOT_DELAY"
run_fast_capture "game-updates" \
  ARCHETYPE_INITIAL_GAME_OVERLAY=updates \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_SCREENSHOT_DELAY"
run_fast_capture "game-hand-card" \
  ARCHETYPE_INITIAL_GAME_OVERLAY=hand_spell \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_SCREENSHOT_DELAY"
run_fast_capture "game-hand-creature" \
  ARCHETYPE_INITIAL_GAME_OVERLAY=hand_creature \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_SCREENSHOT_DELAY"
run_fast_capture "game-placement" \
  ARCHETYPE_INITIAL_GAME_OVERLAY=placement \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_SCREENSHOT_DELAY"
run_fast_capture "game-targeting-spell" \
  ARCHETYPE_INITIAL_GAME_OVERLAY=targeting_spell \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_SCREENSHOT_DELAY"
run_fast_capture "game-targeting-attack" \
  ARCHETYPE_INITIAL_GAME_OVERLAY=targeting_attack \
  ARCHETYPE_SCREENSHOT_DELAY="$GAME_SCREENSHOT_DELAY"
run_capture "game-command-zap-board" \
  ARCHETYPE_SKIP_STACK=0 \
  ARCHETYPE_SKIP_BUILD=1 \
  ARCHETYPE_SKIP_INSTALL=1 \
  ARCHETYPE_INITIAL_GAME_COMMAND=zap_first_enemy_board \
  ARCHETYPE_SCREENSHOT_DELAY=10
run_capture "game-command-play-creature" \
  ARCHETYPE_SKIP_STACK=0 \
  ARCHETYPE_SKIP_BUILD=1 \
  ARCHETYPE_SKIP_INSTALL=1 \
  ARCHETYPE_INITIAL_GAME_COMMAND=play_first_creature \
  ARCHETYPE_SCREENSHOT_DELAY=5
run_capture "game-command-attack" \
  ARCHETYPE_SKIP_STACK=0 \
  ARCHETYPE_SKIP_BUILD=1 \
  ARCHETYPE_SKIP_INSTALL=1 \
  ARCHETYPE_INITIAL_GAME_COMMAND=attack_first_enemy \
  ARCHETYPE_SCREENSHOT_DELAY=5
run_capture "game-command-hero-power" \
  ARCHETYPE_SKIP_STACK=0 \
  ARCHETYPE_SKIP_BUILD=1 \
  ARCHETYPE_SKIP_INSTALL=1 \
  ARCHETYPE_INITIAL_GAME_COMMAND=hero_power \
  ARCHETYPE_SCREENSHOT_DELAY=5
run_capture "game-command-end-turn" \
  ARCHETYPE_SKIP_STACK=0 \
  ARCHETYPE_SKIP_BUILD=1 \
  ARCHETYPE_SKIP_INSTALL=1 \
  ARCHETYPE_INITIAL_GAME_COMMAND=end_turn \
  ARCHETYPE_SCREENSHOT_DELAY=5

# Keep the rapid reseed last so the dashboard and game captures all share the
# default daily-seeded state used by the web reference capture.
run_capture "ranked-queue-rapid" \
  ARCHETYPE_SKIP_STACK=0 \
  ARCHETYPE_SKIP_BUILD=1 \
  ARCHETYPE_SKIP_INSTALL=1 \
  ARCHETYPE_SEED_QUEUE_LADDER=rapid \
  ARCHETYPE_SEED_QUEUE_AGE_SECONDS="$RANKED_QUEUE_SEED_AGE_SECONDS" \
  ARCHETYPE_QUEUE_ELAPSED_SECONDS="$RANKED_QUEUE_ELAPSED_SECONDS" \
  ARCHETYPE_INITIAL_DASHBOARD_SECTION=ranked_queue_rapid \
  ARCHETYPE_SCREENSHOT_DELAY="$RANKED_QUEUE_SCREENSHOT_DELAY"

{
  printf '%s\n' '<!doctype html>'
  printf '%s\n' '<html lang="en">'
  printf '%s\n' '<head>'
  printf '%s\n' '  <meta charset="utf-8">'
  printf '%s\n' '  <meta name="viewport" content="width=device-width, initial-scale=1">'
  printf '%s\n' '  <title>Archetype iOS UI Captures</title>'
  printf '%s\n' '  <style>'
  printf '%s\n' '    :root { color-scheme: dark; font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #111827; color: #f8fafc; }'
  printf '%s\n' '    body { margin: 0; padding: 24px; }'
  printf '%s\n' '    h1 { margin: 0 0 18px; font-size: 22px; }'
  printf '%s\n' '    main { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 18px; align-items: start; }'
  printf '%s\n' '    figure { margin: 0; border: 1px solid #374151; border-radius: 8px; background: #1f2937; overflow: hidden; }'
  printf '%s\n' '    figcaption { padding: 10px 12px; color: #d1d5db; font-size: 13px; font-weight: 700; }'
  printf '%s\n' '    img { display: block; width: 100%; height: auto; background: #020617; }'
  printf '%s\n' '  </style>'
  printf '%s\n' '</head>'
  printf '%s\n' '<body>'
  printf '%s\n' '  <h1>Archetype iOS UI Captures</h1>'
  printf '%s\n' '  <main>'
  for image in "$OUT_DIR"/*.png; do
    [[ -e "$image" ]] || continue
    name="$(basename "$image")"
    printf '    <figure><figcaption>%s</figcaption><img src="%s" alt="%s"></figure>\n' \
      "$name" "$name" "$name"
  done
  printf '%s\n' '  </main>'
  printf '%s\n' '</body>'
  printf '%s\n' '</html>'
} > "$OUT_DIR/index.html"

echo "Saved iOS UI screenshots to $OUT_DIR"
echo "Open $OUT_DIR/index.html to review the capture gallery."

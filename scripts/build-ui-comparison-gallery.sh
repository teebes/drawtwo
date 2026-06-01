#!/usr/bin/env bash
set -euo pipefail

IOS_DIR="${ARCHETYPE_IOS_SCREENSHOT_DIR:-${ARCHETYPE_SCREENSHOT_DIR:-/tmp/archetype-ios-ui}}"
WEB_DIR="${ARCHETYPE_WEB_SCREENSHOT_DIR:-/tmp/archetype-web-ui}"
OUT_DIR="${ARCHETYPE_UI_COMPARISON_DIR:-/tmp/archetype-ui-comparison}"

CAPTURE_ORDER=(
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

contains_name() {
  local target="$1"
  shift

  for name in "$@"; do
    if [[ "$name" == "$target" ]]; then
      return 0
    fi
  done

  return 1
}

is_ios_only_capture() {
  [[ "$1" == "login-confirm.png" ]]
}

mkdir -p "$OUT_DIR"

if [[ ! -d "$IOS_DIR" ]]; then
  echo "Missing iOS screenshot directory: $IOS_DIR" >&2
  exit 1
fi

if [[ ! -d "$WEB_DIR" ]]; then
  echo "Missing web screenshot directory: $WEB_DIR" >&2
  exit 1
fi

image_names=()

for name in "${CAPTURE_ORDER[@]}"; do
  image_name="$name.png"
  if [[ -f "$WEB_DIR/$image_name" || -f "$IOS_DIR/$image_name" ]]; then
    image_names+=("$image_name")
  fi
done

while IFS= read -r image_name; do
  if ! contains_name "$image_name" "${image_names[@]}"; then
    image_names+=("$image_name")
  fi
done < <(
  {
    find "$WEB_DIR" -maxdepth 1 -name '*.png' -print
    find "$IOS_DIR" -maxdepth 1 -name '*.png' -print
  } | awk -F/ '{ print $NF }' | sort -u
)

if command -v swift >/dev/null 2>&1; then
  swift scripts/build-ui-comparison-metrics.swift \
    "$WEB_DIR" \
    "$IOS_DIR" \
    "$OUT_DIR/metrics.tsv" \
    "$OUT_DIR/metrics.html" \
    "${image_names[@]}"
else
  rm -f "$OUT_DIR/metrics.tsv" "$OUT_DIR/metrics.html"
  echo "Swift is not available; skipped UI comparison metrics." >&2
fi

{
  printf '%s\n' '<!doctype html>'
  printf '%s\n' '<html lang="en">'
  printf '%s\n' '<head>'
  printf '%s\n' '  <meta charset="utf-8">'
  printf '%s\n' '  <meta name="viewport" content="width=device-width, initial-scale=1">'
  printf '%s\n' '  <title>Archetype UI Comparison</title>'
  printf '%s\n' '  <style>'
  printf '%s\n' '    :root { color-scheme: dark; font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #111827; color: #f8fafc; }'
  printf '%s\n' '    body { margin: 0; padding: 24px; }'
  printf '%s\n' '    h1 { margin: 0 0 8px; font-size: 22px; }'
  printf '%s\n' '    .meta { margin: 0 0 22px; color: #9ca3af; font-size: 13px; }'
  printf '%s\n' '    .metrics { margin: 0 0 28px; border: 1px solid #374151; border-radius: 8px; background: #1f2937; overflow: hidden; }'
  printf '%s\n' '    .metrics-header { padding: 12px 14px; border-bottom: 1px solid #374151; }'
  printf '%s\n' '    .metrics-header h2 { margin: 0 0 4px; padding: 0; border: 0; font-size: 15px; }'
  printf '%s\n' '    .metrics-header p { margin: 0; color: #9ca3af; font-size: 12px; }'
  printf '%s\n' '    .metrics-table-wrap { overflow-x: auto; }'
  printf '%s\n' '    table { width: 100%; border-collapse: collapse; font-size: 12px; }'
  printf '%s\n' '    th, td { padding: 8px 10px; border-bottom: 1px solid #374151; text-align: left; white-space: nowrap; }'
  printf '%s\n' '    th { color: #d1d5db; background: #111827; font-weight: 700; }'
  printf '%s\n' '    td { color: #e5e7eb; }'
  printf '%s\n' '    tr:last-child td { border-bottom: 0; }'
  printf '%s\n' '    .metric-ok { color: #86efac; }'
  printf '%s\n' '    .metric-watch { color: #facc15; }'
  printf '%s\n' '    .metric-drift { color: #fca5a5; }'
  printf '%s\n' '    main { display: grid; gap: 28px; }'
  printf '%s\n' '    section { border: 1px solid #374151; border-radius: 8px; background: #1f2937; overflow: hidden; }'
  printf '%s\n' '    h2 { margin: 0; padding: 12px 14px; border-bottom: 1px solid #374151; font-size: 15px; }'
  printf '%s\n' '    .pair { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px; background: #374151; align-items: start; }'
  printf '%s\n' '    figure { margin: 0; background: #020617; }'
  printf '%s\n' '    figcaption { padding: 9px 12px; color: #d1d5db; font-size: 12px; font-weight: 700; background: #111827; }'
  printf '%s\n' '    img { display: block; width: 100%; height: auto; background: #020617; }'
  printf '%s\n' '    .overlay-frame { position: relative; overflow: hidden; background: #020617; }'
  printf '%s\n' '    .overlay-frame img:first-child { position: relative; }'
  printf '%s\n' '    .overlay-frame img.overlay-ios { position: absolute; inset: 0; opacity: 0.52; }'
  printf '%s\n' '    .overlay-note { padding: 8px 12px; color: #9ca3af; font-size: 11px; background: #020617; border-top: 1px solid #1f2937; }'
  printf '%s\n' '    .missing { padding: 24px; color: #fca5a5; font-size: 13px; }'
  printf '%s\n' '    @media (max-width: 760px) { .pair { grid-template-columns: 1fr; } }'
  printf '%s\n' '  </style>'
  printf '%s\n' '</head>'
  printf '%s\n' '<body>'
  printf '%s\n' '  <h1>Archetype UI Comparison</h1>'
  printf '  <p class="meta">Web: %s<br>iOS: %s</p>\n' "$WEB_DIR" "$IOS_DIR"
  if [[ -f "$OUT_DIR/metrics.html" ]]; then
    cat "$OUT_DIR/metrics.html"
  fi
  printf '%s\n' '  <main>'

  for name in "${image_names[@]}"; do
    ios_image="$IOS_DIR/$name"
    web_image="$WEB_DIR/$name"

    printf '    <section>\n'
    printf '      <h2>%s</h2>\n' "$name"
    printf '      <div class="pair">\n'

    printf '        <figure><figcaption>Web</figcaption>'
    if [[ -f "$web_image" ]]; then
      printf '<img src="%s" alt="Web %s">' "$web_image" "$name"
    elif is_ios_only_capture "$name"; then
      printf '<div class="missing">Native-only screen</div>'
    else
      printf '<div class="missing">No web capture</div>'
    fi
    printf '</figure>\n'

    printf '        <figure><figcaption>iOS</figcaption>'
    if [[ -f "$ios_image" ]]; then
      printf '<img src="%s" alt="iOS %s">' "$ios_image" "$name"
    else
      printf '<div class="missing">No iOS capture</div>'
    fi
    printf '</figure>\n'

    printf '        <figure><figcaption>Overlay</figcaption>'
    if [[ -f "$web_image" && -f "$ios_image" ]]; then
      printf '<div class="overlay-frame"><img src="%s" alt="Web overlay base %s"><img class="overlay-ios" src="%s" alt="iOS overlay %s"></div><div class="overlay-note">iOS is drawn over web at 52%% opacity.</div>' "$web_image" "$name" "$ios_image" "$name"
    elif is_ios_only_capture "$name"; then
      printf '<div class="missing">Native-only screen</div>'
    else
      printf '<div class="missing">Overlay requires both captures</div>'
    fi
    printf '</figure>\n'

    printf '      </div>\n'
    printf '    </section>\n'
  done

  printf '%s\n' '  </main>'
  printf '%s\n' '</body>'
  printf '%s\n' '</html>'
} > "$OUT_DIR/index.html"

echo "Saved UI comparison gallery to $OUT_DIR/index.html"

if command -v swift >/dev/null 2>&1; then
  swift scripts/build-ui-comparison-contact-sheet.swift \
    "$WEB_DIR" \
    "$IOS_DIR" \
    "$OUT_DIR/contact-sheet.png" \
    "${image_names[@]}"
else
  echo "Swift is not available; skipped UI comparison contact sheet." >&2
fi

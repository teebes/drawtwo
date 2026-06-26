# Archetype iOS Client

Native SwiftUI client for the Archetype title. It talks directly to the DrawTwo
backend. By default it uses production at `https://drawtwo.com`; simulator runs
can point at a local Docker backend with launch environment variables.

The iOS app focuses on player workflows. Builder, title configuration, card
editing, Control Panel, and Game Config workflows remain web-only. Collection
and deck screens let players inspect cards, create decks, edit deck metadata,
archive decks, and manage the cards assigned to their decks.

## What Works

- Passwordless DrawTwo login using the existing email-confirm endpoint.
- App-targeted email login links using Universal Links on
  `https://drawtwo.com/app/login/<key>`, with `drawtwo://login/<key>`,
  paste-key, and browser fallback support.
- Secure token storage in iOS Keychain.
- Session refresh through the existing JWT refresh endpoint.
- Archetype dashboard, notifications, active games, title stats, and embedded
  leaderboard preview.
- Collection, deck detail, collection card detail, and deck card detail views.
- Native deck creation, deck metadata editing, deck archiving, card add/remove,
  and deck card count management.
- PvE opponent loading from `/api/titles/archetype/pve/`.
- PvE game creation, ranked queue entry/leave flows, friendly challenge sending,
  accepting, declining, and cancelling.
- Games history with ranked/friendly summaries and pagination.
- Standalone leaderboard, friends, profile, and how-to-play screens.
- Game detail loading from `/api/gameplay/games/<id>/`, including board state,
  mulligan, hand details, placement, targeting, attacks, hero powers, end turn,
  concede, updates, game menu, game-over/rating changes, and friendly rematch.
- User and game WebSocket connections using the existing JWT query token.
- WebSocket requests include an `Origin` matching the configured backend, which
  the Django Channels `AllowedHostsOriginValidator` requires.
- Local simulator login against seeded Docker data in development builds.
- Visual QA harnesses that capture matched mobile-width web and iOS screenshots
  from deterministic local backend data.

## Current Limits

- Universal Links require the deployed `drawtwo.com` frontend to serve the
  Apple App Site Association file and the signing team to allow Associated
  Domains for `com.drawtwo.archetype.dev`.
- There is no StoreKit subscription layer yet.
- App Store metadata is not prepared yet.
- Android is not implemented yet.

## Local Backend UI Testing

For visual parity work, use the full comparison wrapper first:

```sh
ARCHETYPE_UI_COMPARISON_DIR=/tmp/archetype-ui-comparison-review \
scripts/capture-ui-comparison.sh
```

That brings up Docker, seeds deterministic local data, captures the mobile web
frontend, reseeds, captures the iOS simulator from the same local backend, and
builds review artifacts:

- `/tmp/archetype-ui-comparison-review/index.html` for per-screen web, iOS, and
  overlay comparison.
- `/tmp/archetype-ui-comparison-review/contact-sheet.png` for a fast visual
  sweep across the whole app.
- `/tmp/archetype-ui-comparison-review/metrics.tsv` for a rough shortlist of
  screens whose scaled screenshots diverge most.

Use the metrics only as triage. Native safe areas, Dynamic Island spacing, and
home indicator space are expected to differ from the Vue mobile viewport, so the
contact sheet and overlay view are the source of truth before making UI changes.

The fastest repeatable loop is:

```sh
scripts/run-ios-local-ui.sh
```

That starts Docker, runs migrations, seeds deterministic Archetype data, builds
the app for the booted simulator, installs it, and launches with automatic local
sign-in enabled.

The runner chooses the newest installed Pro simulator it knows about, preferring
`iPhone 17 Pro`, then `iPhone 16 Pro`, then `iPhone 15 Pro`. Override that when
you need a specific device:

```sh
SIMULATOR_NAME="iPhone 17 Pro" scripts/run-ios-local-ui.sh
```

The runner resolves the selected simulator to a concrete device UDID and uses
that same device for build, install, launch, screenshots, and state assertions.
If you have multiple matching simulators or multiple devices booted, pass
`SIMULATOR_UDID=<device-udid>` to force an exact target.

To validate the production-looking logged-out login screen instead, disable
automatic sign-in and clear any stored simulator session for this launch:

```sh
ARCHETYPE_AUTO_LOGIN=0 \
ARCHETYPE_CLEAR_SESSION=1 \
ARCHETYPE_SCREENSHOT_PATH=/tmp/archetype-login.png \
scripts/run-ios-local-ui.sh
```

To launch directly into the native sign-up state for visual QA:

```sh
ARCHETYPE_AUTO_LOGIN=0 \
ARCHETYPE_CLEAR_SESSION=1 \
ARCHETYPE_INITIAL_LOGIN_MODE=signup \
ARCHETYPE_SCREENSHOT_PATH=/tmp/archetype-login-signup.png \
scripts/run-ios-local-ui.sh
```

To launch directly into the native confirmation fallback form:

```sh
ARCHETYPE_AUTO_LOGIN=0 \
ARCHETYPE_CLEAR_SESSION=1 \
ARCHETYPE_INITIAL_LOGIN_MODE=confirm \
ARCHETYPE_SCREENSHOT_PATH=/tmp/archetype-login-confirm.png \
scripts/run-ios-local-ui.sh
```

If you need to paste an existing email confirmation URL, app link, or raw key
without sending a new link first, add
`ARCHETYPE_SHOW_MANUAL_LOGIN_LINK_SHORTCUT=1` to expose the manual shortcut
below the login card.

For visual QA, you can launch directly to a native screen:

```sh
ARCHETYPE_INITIAL_DASHBOARD_SECTION=how_to scripts/run-ios-local-ui.sh
```

Supported screen values are `how_to`, `games`, `collection`, `deck`,
`new_game`, `new_game_ai`, `leaderboard`, `friends`, `profile`,
`ranked_queue_daily`, and `ranked_queue_rapid`. `deck` opens the selected seeded
deck by default; pass `ARCHETYPE_INITIAL_DECK_ID=<id>` to open a specific deck.
To inspect the lower sections of the dashboard itself, use `scroll_how_to`.
Use `scroll_leaderboard` to inspect the embedded dashboard leaderboard preview.

To inspect the authenticated dashboard menu, open the dashboard and set
`ARCHETYPE_INITIAL_PROFILE_MENU=1`.

For profile write-path checks against the local backend, open Profile with a
draft username and optionally save it automatically:

```sh
ARCHETYPE_INITIAL_DASHBOARD_SECTION=profile \
ARCHETYPE_INITIAL_PROFILE_USERNAME=NativePilot \
ARCHETYPE_INITIAL_PROFILE_SAVE=1 \
ARCHETYPE_EXPECTED_CAPTURE_STATE=profile \
ARCHETYPE_EXPECTED_CAPTURE_DETAIL=username=NativePilot \
scripts/run-ios-local-ui.sh
```

The runner can also save a simulator screenshot after launch:

```sh
ARCHETYPE_INITIAL_DASHBOARD_SECTION=collection \
ARCHETYPE_SCREENSHOT_PATH=/tmp/archetype-collection.png \
scripts/run-ios-local-ui.sh
```

For Collection card detail screenshots, open the Collection screen and set
`ARCHETYPE_INITIAL_COLLECTION_CARD_SLUG=first` or pass a specific card slug:

```sh
ARCHETYPE_INITIAL_DASHBOARD_SECTION=collection \
ARCHETYPE_INITIAL_COLLECTION_CARD_SLUG=zap \
ARCHETYPE_SCREENSHOT_PATH=/tmp/archetype-card-detail.png \
scripts/run-ios-local-ui.sh
```

For Deck card detail screenshots, open the seeded deck and set
`ARCHETYPE_INITIAL_DECK_CARD_SLUG=first` or pass a specific card slug:

```sh
ARCHETYPE_INITIAL_DASHBOARD_SECTION=deck \
ARCHETYPE_INITIAL_DECK_CARD_SLUG=bandage \
ARCHETYPE_SCREENSHOT_PATH=/tmp/archetype-deck-card-detail.png \
scripts/run-ios-local-ui.sh
```

Use `ARCHETYPE_SCREENSHOT_DELAY=<seconds>` if a screen needs more time to load.
The capture suite defaults to a slightly slower native route delay than the web
capture so pushed SwiftUI screens have time to finish loading before screenshots
are taken. It also uses `ARCHETYPE_GAME_SCREENSHOT_DELAY=8` for gameplay
screens, `ARCHETYPE_GAME_HERO_SCREENSHOT_DELAY=15` for hero-detail overlays
that need remote hero artwork to finish loading,
`ARCHETYPE_LEADERBOARD_SCREENSHOT_DELAY=8` for the standalone leaderboard
capture, and
`ARCHETYPE_RANKED_QUEUE_SCREENSHOT_DELAY=6` for ranked queue captures so pushed
SwiftUI screens have time to settle before the timer screenshot is taken;
override any of those when a slower machine needs more time.

To capture a synced web/native visual comparison suite, use the wrapper:

```sh
scripts/capture-ui-comparison.sh
```

That starts and seeds the local Docker backend for the web capture, captures the
web reference screens, reseeds the backend, captures iOS from the same
already-running deterministic local seed,
scales the iOS screenshots to the web viewport width for easier point-for-point
review, verifies that every expected web and iOS screenshot exists with valid
image dimensions, and writes `/tmp/archetype-ui-comparison/index.html` plus
`/tmp/archetype-ui-comparison/contact-sheet.png` for quick visual review. The
wrapper uses platform-specific expectations: web captures only comparable web
states, while iOS also requires native-only states such as the confirmation
fallback form. The wrapper defaults `ARCHETYPE_SEED_GAME_AGE_SECONDS` to
`-3600`, which future-dates seeded game timestamps so both web and iOS render
relative game times as `Just now` throughout the long comparison run. Override
that when intentionally validating relative-time copy. Web captures also freeze
CSS animations by default with `ARCHETYPE_VISUAL_CAPTURE_FREEZE_ANIMATIONS=1`,
and iOS captures launch with `ARCHETYPE_VISUAL_CAPTURE=1`, so animated surfaces
like ranked queue do not drift between screenshot runs. Even when
`ARCHETYPE_SKIP_STACK=1` is set, the wrapper
reseeds before the web pass by default so stale state from an earlier run cannot
make the screenshots incomparable. Set
`ARCHETYPE_RESEED_BEFORE_WEB_CAPTURE=0` or
`ARCHETYPE_RESEED_BEFORE_IOS_CAPTURE=0` only when intentionally debugging
existing local state. When Swift is available, the gallery also includes a
comparison-metrics table and writes `/tmp/archetype-ui-comparison/metrics.tsv`
with each screen's dimensions, height delta, best vertical shift, full-frame
aligned mean RGB delta, full-frame aligned changed-pixel percentage, content
crop top, content mean RGB delta, and content changed-pixel percentage. The
content columns use the same vertical alignment pass, then ignore
screen-specific top chrome plus the bottom 34px of the shared screenshot area
so normal iOS safe-area, page-banner, and home-indicator differences do not
dominate the shortlist. The gallery sorts those rows by content RGB delta when
available, falling back to the full-frame RGB delta, so the largest likely
content differences appear first. Treat those metrics as triage signals, not
pass/fail gates; native safe areas still need visual review.

Override the output folders with `ARCHETYPE_WEB_SCREENSHOT_DIR`,
`ARCHETYPE_IOS_RAW_SCREENSHOT_DIR`, `ARCHETYPE_IOS_SCREENSHOT_DIR`, and
`ARCHETYPE_UI_COMPARISON_DIR`.

For faster iteration on one screen or a small cluster of screens, pass a comma-
or space-separated `ARCHETYPE_CAPTURE_NAMES` list. The comparison wrapper passes
that same filter through to both web and iOS capture suites:

```sh
ARCHETYPE_CAPTURE_NAMES=login,login-signup \
ARCHETYPE_UI_COMPARISON_DIR=/tmp/archetype-ui-comparison-login \
scripts/capture-ui-comparison.sh
```

Use the capture names shown in the gallery, such as `new-game`,
`game-hand-card`, or `profile-edit`. The first selected iOS capture still does
the Docker seed/build/install setup, then later selected captures reuse the
installed simulator app.

The same filter is available through Make as
`make ios-ui-comparison SCREENS=profile-edit` or
`make ios-ui-captures SCREENS=game-command-zap-board`.

To capture only a repeatable visual QA suite across the main playable iOS
screens:

```sh
scripts/capture-ios-ui.sh
```

That writes PNGs to `/tmp/archetype-ios-ui` by default. Override the destination
with `ARCHETYPE_IOS_SCREENSHOT_DIR=/tmp/my-ios-screenshots` or
`ARCHETYPE_SCREENSHOT_DIR=/tmp/my-ios-screenshots`. The script also writes an
`index.html` file in the screenshot directory so the full capture set can be
reviewed as a gallery in a browser. The suite does one full Docker
seed/build/install pass, then reuses the installed app for the remaining
launches. It captures logged-out login, sign-up, and native confirmation states,
both player and AI new-game states, reseeds once with a rapid queue entry so
both daily and rapid queue screens are captured, and keeps the rapid reseed at
the end so the dashboard and game captures stay in the default daily-seeded
state. The suite also reseeds isolated games for deterministic post-command
checks, including a targeted spell on the board, creature play, creature
attack, hero power, and end-turn flows into the updates sheet.
Gameplay captures include core play-only overlays for mulligan, hand card
detail, creature placement, spell targeting, attack targeting, game updates, and
the game menu.

To capture the matching mobile-width web reference screens from the same seeded
local backend:

```sh
scripts/capture-web-ui.sh
```

That writes PNGs to `/tmp/archetype-web-ui` by default. Override the destination
with `ARCHETYPE_WEB_SCREENSHOT_DIR=/tmp/my-web-screenshots`. The script starts
and seeds Docker unless `ARCHETYPE_SKIP_STACK=1` is set, signs into the web app
as `ios@devdata.local`, captures at a 390x844 viewport, and writes an
`index.html` gallery next to the PNGs. Use this gallery as the web baseline
when checking whether the native screens still match the Vue frontend.

After both individual suites have run, build a comparison page:

```sh
scripts/build-ui-comparison-gallery.sh
```

By default it compares `/tmp/archetype-web-ui` and `/tmp/archetype-ios-ui`, then
writes `/tmp/archetype-ui-comparison/index.html` and, when Swift is available,
`/tmp/archetype-ui-comparison/contact-sheet.png` plus
`/tmp/archetype-ui-comparison/metrics.tsv`. Each HTML capture includes web, iOS,
and overlay columns; the overlay draws the iOS screenshot over the web reference
so spacing, size, and alignment differences are easier to spot. The PNG contact
sheet shows the web and iOS captures side by side in workflow order, which is
faster for broad visual sweeps. The metrics table highlights screens whose
scaled captures diverge most after a small vertical alignment pass, giving a
quick shortlist for manual review without over-ranking normal iOS safe-area
offsets. The gallery renders the known capture suite in workflow order, with any
extra PNGs appended afterward, so related screens stay together during review.
Override the input or output folders with `ARCHETYPE_WEB_SCREENSHOT_DIR`,
`ARCHETYPE_IOS_SCREENSHOT_DIR`, and `ARCHETYPE_UI_COMPARISON_DIR`.

The local seed defaults to a daily ranked queue entry. To validate the rapid
queue timer screen directly:

```sh
ARCHETYPE_SEED_QUEUE_LADDER=rapid \
ARCHETYPE_INITIAL_DASHBOARD_SECTION=ranked_queue_rapid \
ARCHETYPE_SCREENSHOT_PATH=/tmp/archetype-rapid-queue.png \
scripts/run-ios-local-ui.sh
```

Queue screenshots can otherwise drift because the visible timer includes the
time spent launching the simulator and navigating to the screen. For direct
debug launches, set `ARCHETYPE_QUEUE_ELAPSED_SECONDS=<seconds>` to freeze the
visible rapid-queue timer for screenshot capture. For the full iOS capture
suite, use `ARCHETYPE_RANKED_QUEUE_ELAPSED_SECONDS`, which defaults to `3` so
the native rapid queue lands on the same early timer state as the web reference.
For the comparison wrapper, use `ARCHETYPE_IOS_RANKED_QUEUE_ELAPSED_SECONDS`
and `ARCHETYPE_WEB_QUEUE_CAPTURE_AGE_SECONDS` to control the native and web
queue captures independently. If you need to test timestamp-derived queue age
instead, set `ARCHETYPE_SEED_QUEUE_AGE_SECONDS=<seconds>` on
`scripts/run-ios-local-ui.sh`; negative values place the seeded queue timestamp
slightly in the future.

For deterministic games-list timestamps outside the comparison wrapper, set
`ARCHETYPE_SEED_GAME_AGE_SECONDS=<seconds>` on `scripts/run-ios-local-ui.sh`,
`scripts/capture-web-ui.sh`, or `scripts/capture-ios-ui.sh`. Negative values
future-date seeded games, which both clients display as `Just now`.
For direct simulator screenshots, set `ARCHETYPE_VISUAL_CAPTURE=1` to freeze
native capture-only animations while leaving normal debug launches unchanged.
The iOS capture suite also enables `ARCHETYPE_CAPTURE_STATE=1` and passes an
expected state marker for every screenshot. After each simulator screenshot,
`scripts/run-ios-local-ui.sh` reads the app's debug-only
`archetype_capture_state.json` file from the simulator container and fails if
the active screen is not the expected login, dashboard, collection, queue, or
gameplay state. For one-off screenshots, set
`ARCHETYPE_EXPECTED_CAPTURE_STATE=<screen>` to get the same guard. Command
captures can also assert debug state details such as
`ARCHETYPE_EXPECTED_CAPTURE_DETAIL=latest_update_type=update_damage`, which
guards against screenshots where the command did not actually resolve.

You can also launch directly into a seeded game, and in development builds open
specific in-game overlays for simulator screenshots:

```sh
ARCHETYPE_INITIAL_GAME_ID=latest scripts/run-ios-local-ui.sh
```

Use `latest` or `active` to resolve the seeded active game after the script
runs migrations and refreshes local data. Use `latest_ended_ranked` to open a
seeded finished ranked game and inspect the game-over/rating-change overlay.
Use `latest_mulligan` to open the seeded game with the opening-hand mulligan
overlay. Specific numeric IDs are still supported when you need one.

```sh
ARCHETYPE_INITIAL_GAME_OVERLAY=placement \
scripts/run-ios-local-ui.sh
```

Supported overlay values are `menu`, `updates`, `hand_card`, `hand_spell`,
`hand_creature`, `placement`, `targeting_spell`, `own_hero`, `opponent_hero`,
`own_creature`, `opponent_creature`, and `targeting_attack`. When an overlay is
provided without `ARCHETYPE_INITIAL_GAME_ID`, the script opens the latest seeded
active game.

For post-action UI checks, the runner can also send a deterministic game command
after launch and then open the updates sheet:

```sh
ARCHETYPE_INITIAL_GAME_COMMAND=zap_first_enemy scripts/run-ios-local-ui.sh
```

Supported command values are `zap_first_enemy`, `attack_first_enemy`,
`hero_power`, `hero_power_self`, `play_first_creature`, and `end_turn`. Add
`_board` to keep the app on the board after the command instead of opening the
updates sheet, for example `zap_first_enemy_board`.

To run the steps manually, start and seed the local backend:

```sh
docker compose up -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_archetype_dev
```

Build for the simulator, install the app, then launch it against local Docker:

```sh
xcodebuild \
  -project ios/Archetype/Archetype.xcodeproj \
  -scheme Archetype \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
  CODE_SIGNING_ALLOWED=NO \
  build

xcrun simctl install booted \
  ~/Library/Developer/Xcode/DerivedData/Archetype-*/Build/Products/Debug-iphonesimulator/Archetype.app

SIMCTL_CHILD_ARCHETYPE_BACKEND_BASE_URL=http://127.0.0.1:8002 \
SIMCTL_CHILD_ARCHETYPE_AUTO_LOGIN=1 \
xcrun simctl launch --terminate-running-process booted com.drawtwo.archetype.dev
```

The seeded local player account is `ios@devdata.local` with password `password`.
The seeded title author is a separate `author@devdata.local` account. The web
reference screenshot script also hides deck-owner editing and collection deck
creation controls so local comparisons stay focused on the iOS play-only scope.
Set `ARCHETYPE_SHOW_LOCAL_ACCOUNT_SHORTCUT=1` when launching against a local
backend if you want the login screen to show a `Use Local Test Account` button.
The visual QA captures leave local and manual shortcuts hidden so the logged-out
screen stays close to the web frontend.

For physical iPhone testing against local Docker, use your Mac's LAN address
instead of `127.0.0.1`. The backend publishes port `8002`, so if your Mac is
`192.168.1.25`, set this environment variable in Xcode's Run scheme:

```sh
ARCHETYPE_BACKEND_BASE_URL=http://192.168.1.25:8002
```

The debug build treats localhost, `.local` hostnames, and private LAN addresses
as local backends. Add `ARCHETYPE_SHOW_LOCAL_ACCOUNT_SHORTCUT=1` to the Run
scheme if you want the local test-account shortcut on the phone. iOS may ask for
local network permission the first time the app connects to your Mac.

## Test On An iPhone

1. Install Xcode from the Mac App Store. Use a version that supports the iOS
   version installed on your iPhone 17 Pro.
2. Open `ios/Archetype/Archetype.xcodeproj` in Xcode.
3. In Xcode, select the `Archetype` target, open `Signing & Capabilities`, and
   choose your Apple developer team or personal team.
4. If Xcode reports that the bundle identifier is taken, change
   `com.drawtwo.archetype.dev` to something unique, such as
   `com.yourname.archetype.dev`.
5. Connect your iPhone by USB, or pair it through Xcode's Devices and Simulators
   window for wireless debugging.
6. Select your iPhone as the run destination.
7. Press Run.
8. On the phone, enter the email for your existing DrawTwo account and tap
   `Send Login Link`.
9. Open the email on the phone and tap the `https://drawtwo.com/app/login/<key>`
   link. The app should foreground and sign in. If the email client opens the
   browser instead, tap `Open DrawTwo App`, use the `drawtwo://login/<key>`
   fallback, or copy the confirmation code and paste it into the app.
10. After login, choose a deck and PvE opponent, then start a practice game.

To test the production login workflow from a dev build, remove any
`ARCHETYPE_BACKEND_BASE_URL` override from the Xcode scheme so the app uses
`https://drawtwo.com`. Install the dev build after the Associated Domains
entitlement is present; iOS fetches the association file on install/update and
may cache old results for a while.

To test against your local Docker backend on the phone, first run
`docker compose up -d` and `docker compose exec backend python manage.py seed_archetype_dev`
on the Mac. Then edit the Xcode scheme for the `Archetype` target, open
`Run > Arguments`, add `ARCHETYPE_BACKEND_BASE_URL=http://<your-mac-ip>:8002`,
optionally add `ARCHETYPE_SHOW_LOCAL_ACCOUNT_SHORTCUT=1` or
`ARCHETYPE_SHOW_MANUAL_LOGIN_LINK_SHORTCUT=1`, and run the app on the phone. Use
the shortcut or the seeded `ios@devdata.local` account.

## Simulator Log Notes

The simulator may print noisy system messages about eligibility plists, app
launch measurements, keyboard constraints, CoreAudio, or loudness manager
streams. Those are simulator/runtime messages and are not DrawTwo failures. The
important networking error to watch for is a `URLSessionWebSocketTask` handshake
failure; this prototype sets the required `Origin` header for drawtwo.com.

If your account has no Archetype decks, create one on the web app first at
`https://drawtwo.com`.

## Build From Terminal

For a simulator sanity check:

```sh
xcodebuild \
  -project ios/Archetype/Archetype.xcodeproj \
  -scheme Archetype \
  -destination 'generic/platform=iOS Simulator' \
  CODE_SIGNING_ALLOWED=NO \
  build
```

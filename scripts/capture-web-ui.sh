#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${ARCHETYPE_WEB_SCREENSHOT_DIR:-/tmp/archetype-web-ui}"
BASE_URL="${ARCHETYPE_WEB_BASE_URL:-http://localhost:3000}"
API_BASE_URL="${ARCHETYPE_API_BASE_URL:-http://localhost:8002/api}"
SCREENSHOT_DELAY="${ARCHETYPE_WEB_SCREENSHOT_DELAY:-3}"
VIEWPORT_WIDTH="${ARCHETYPE_WEB_VIEWPORT_WIDTH:-390}"
VIEWPORT_HEIGHT="${ARCHETYPE_WEB_VIEWPORT_HEIGHT:-844}"
SEED_QUEUE_LADDER="${ARCHETYPE_SEED_QUEUE_LADDER:-daily}"
SEED_QUEUE_AGE_SECONDS="${ARCHETYPE_SEED_QUEUE_AGE_SECONDS:-0}"
SEED_GAME_AGE_SECONDS="${ARCHETYPE_SEED_GAME_AGE_SECONDS:-0}"
QUEUE_CAPTURE_AGE_SECONDS="${ARCHETYPE_QUEUE_CAPTURE_AGE_SECONDS:-0}"
SKIP_STACK="${ARCHETYPE_SKIP_STACK:-0}"
VISUAL_CAPTURE_FREEZE_ANIMATIONS="${ARCHETYPE_VISUAL_CAPTURE_FREEZE_ANIMATIONS:-1}"
CHROME_DEBUG_PORT="${ARCHETYPE_CHROME_DEBUG_PORT:-$((9300 + RANDOM % 500))}"
CHROME_PATH="${ARCHETYPE_CHROME_PATH:-}"
CAPTURE_NAMES="${ARCHETYPE_CAPTURE_NAMES:-}"

mkdir -p "$OUT_DIR"
find "$OUT_DIR" -maxdepth 1 -type f \( -name '*.png' -o -name 'index.html' \) -delete

truthy() {
  [[ "$1" == "1" || "$1" == "true" || "$1" == "yes" || "$1" == "on" ]]
}

if [[ -z "$CHROME_PATH" ]]; then
  for candidate in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Chromium.app/Contents/MacOS/Chromium"
  do
    if [[ -x "$candidate" ]]; then
      CHROME_PATH="$candidate"
      break
    fi
  done
fi

if [[ -z "$CHROME_PATH" || ! -x "$CHROME_PATH" ]]; then
  echo "Google Chrome or Chromium is required. Set ARCHETYPE_CHROME_PATH to its executable." >&2
  exit 1
fi

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

resolve_first_deck_id() {
  docker compose exec -T backend python manage.py shell -c \
    "from django.contrib.auth import get_user_model; from apps.collection.models import Deck; user = get_user_model().objects.get(email='ios@devdata.local'); deck = Deck.objects.filter(user=user, title__slug='archetype', archived_at__isnull=True).order_by('id').first(); print(deck.id if deck else '')" \
    | tr -d '\r' \
    | tail -n 1
}

resolve_first_card_slug() {
  docker compose exec -T backend python manage.py shell -c \
    "from apps.builder.models import CardTemplate, Title; title = Title.objects.filter(slug='archetype', is_latest=True).first(); card = CardTemplate.objects.filter(title=title, is_latest=True, is_collectible=True).order_by('cost', 'name').first() if title else None; print(card.slug if card else '')" \
    | tr -d '\r' \
    | tail -n 1
}

LATEST_GAME_ID="$(resolve_latest_game_id)"
LATEST_MULLIGAN_GAME_ID="$(resolve_latest_game_id mulligan)"
LATEST_ENDED_RANKED_GAME_ID="$(resolve_latest_ended_ranked_game_id)"
FIRST_DECK_ID="$(resolve_first_deck_id)"
FIRST_CARD_SLUG="$(resolve_first_card_slug)"

TOKEN_JSON="$(
  curl -fsS \
    -X POST "$API_BASE_URL/auth/token/" \
    -H "Content-Type: application/json" \
    -d '{"email":"ios@devdata.local","password":"password"}'
)"

ACCESS_TOKEN="$(
  printf '%s' "$TOKEN_JSON" \
    | node -e 'let s = ""; process.stdin.on("data", d => s += d); process.stdin.on("end", () => process.stdout.write(JSON.parse(s).access));'
)"

REFRESH_TOKEN="$(
  printf '%s' "$TOKEN_JSON" \
    | node -e 'let s = ""; process.stdin.on("data", d => s += d); process.stdin.on("end", () => process.stdout.write(JSON.parse(s).refresh));'
)"

USER_JSON="$(
  curl -fsS \
    "$API_BASE_URL/auth/profile/" \
    -H "Authorization: Bearer $ACCESS_TOKEN"
)"

CAPTURES_JSON="$(
  node - <<NODE
const captures = [
  ["dashboard", "/archetype"],
  ["dashboard-how-to", "/archetype"],
  ["profile-menu", "/archetype"],
  ["games", "/archetype/games"],
  ["collection", "/archetype/collection"],
  ["new-game", "/archetype/games/new"],
  ["new-game-ai", "/archetype/games/new"],
  ["leaderboard", "/archetype/leaderboard"],
  ["friends", "/friends"],
  ["profile", "/profile"],
  ["profile-edit", "/profile"],
  ["how-to", "/howto"],
];

if ("$FIRST_DECK_ID") {
  captures.push(["deck", "/archetype/decks/$FIRST_DECK_ID"]);
  captures.push(["deck-card-detail", "/archetype/decks/$FIRST_DECK_ID"]);
}

if ("$FIRST_CARD_SLUG") {
  captures.push(["collection-card-detail", "/archetype/cards/$FIRST_CARD_SLUG/details"]);
}

if ("$LATEST_GAME_ID") {
  captures.push(["game-board", "/archetype/games/$LATEST_GAME_ID"]);
}

if ("$LATEST_MULLIGAN_GAME_ID") {
  captures.push(["game-mulligan", "/archetype/games/$LATEST_MULLIGAN_GAME_ID"]);
}

if ("$LATEST_ENDED_RANKED_GAME_ID") {
  captures.push(["game-over-ranked", "/archetype/games/$LATEST_ENDED_RANKED_GAME_ID"]);
}

process.stdout.write(JSON.stringify(captures));
NODE
)"

echo "Capturing web UI references into $OUT_DIR..."

OUT_DIR="$OUT_DIR" \
BASE_URL="$BASE_URL" \
SCREENSHOT_DELAY="$SCREENSHOT_DELAY" \
VIEWPORT_WIDTH="$VIEWPORT_WIDTH" \
VIEWPORT_HEIGHT="$VIEWPORT_HEIGHT" \
CHROME_DEBUG_PORT="$CHROME_DEBUG_PORT" \
CHROME_PATH="$CHROME_PATH" \
ACCESS_TOKEN="$ACCESS_TOKEN" \
REFRESH_TOKEN="$REFRESH_TOKEN" \
USER_JSON="$USER_JSON" \
CAPTURES_JSON="$CAPTURES_JSON" \
API_BASE_URL="$API_BASE_URL" \
FIRST_DECK_ID="$FIRST_DECK_ID" \
QUEUE_CAPTURE_AGE_SECONDS="$QUEUE_CAPTURE_AGE_SECONDS" \
VISUAL_CAPTURE_FREEZE_ANIMATIONS="$VISUAL_CAPTURE_FREEZE_ANIMATIONS" \
CAPTURE_NAMES="$CAPTURE_NAMES" \
node - <<'NODE'
const { execFile, spawn } = await import("node:child_process");
const fs = await import("node:fs/promises");
const path = await import("node:path");
const { promisify } = await import("node:util");

const outDir = process.env.OUT_DIR;
const baseUrl = process.env.BASE_URL.replace(/\/$/, "");
const screenshotDelayMs = Math.max(0, Number(process.env.SCREENSHOT_DELAY || 3) * 1000);
const viewportWidth = Number(process.env.VIEWPORT_WIDTH || 390);
const viewportHeight = Number(process.env.VIEWPORT_HEIGHT || 844);
const port = Number(process.env.CHROME_DEBUG_PORT || 9333);
const profileDir = path.join("/tmp", `archetype-web-capture-${Date.now()}-${Math.random().toString(16).slice(2)}`);
const captures = JSON.parse(process.env.CAPTURES_JSON || "[]");
const selectedCaptureNames = new Set(
  String(process.env.CAPTURE_NAMES || "")
    .split(/[,\s]+/)
    .map((name) => name.trim())
    .filter(Boolean)
);
const hasCaptureFilter = selectedCaptureNames.size > 0;
const shouldCapture = (name) => !hasCaptureFilter || selectedCaptureNames.has(name);
const apiBaseUrl = process.env.API_BASE_URL.replace(/\/$/, "");
const wsBaseUrl = apiBaseUrl.replace(/\/api$/, "").replace(/^http/, "ws");
const firstDeckId = process.env.FIRST_DECK_ID;
const freezeAnimations = ["1", "true", "yes", "on"].includes(
  String(process.env.VISUAL_CAPTURE_FREEZE_ANIMATIONS || "").toLowerCase()
);
const execFileAsync = promisify(execFile);

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForChrome() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) {
        return;
      }
    } catch {
      // Keep waiting for the remote debugger to come up.
    }
    await sleep(100);
  }
  throw new Error("Chrome remote debugger did not start.");
}

async function createTarget() {
  const response = await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, {
    method: "PUT",
  });
  if (!response.ok) {
    throw new Error(`Failed to create Chrome target: ${response.status}`);
  }
  return response.json();
}

function createSession(webSocketUrl) {
  const socket = new WebSocket(webSocketUrl);
  let nextId = 0;
  const pending = new Map();
  const listeners = new Map();

  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) {
        reject(new Error(message.error.message));
      } else {
        resolve(message.result);
      }
    }

    const methodListeners = listeners.get(message.method) || [];
    for (const listener of methodListeners) {
      listener(message.params);
    }
  };

  const opened = new Promise((resolve, reject) => {
    socket.onopen = resolve;
    socket.onerror = reject;
  });

  const send = (method, params = {}) => {
    const id = ++nextId;
    socket.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
    });
  };

  const once = (method) => (
    new Promise((resolve) => {
      const listener = (params) => {
        listeners.set(
          method,
          (listeners.get(method) || []).filter((candidate) => candidate !== listener)
        );
        resolve(params);
      };
      listeners.set(method, [...(listeners.get(method) || []), listener]);
    })
  );

  return { opened, send, once, close: () => socket.close() };
}

async function writeGallery() {
  const files = (await fs.readdir(outDir))
    .filter((file) => file.endsWith(".png"))
    .sort();

  const figures = files.map((file) => (
    `    <figure><figcaption>${file}</figcaption><img src="${file}" alt="${file}"></figure>`
  )).join("\n");

  await fs.writeFile(
    path.join(outDir, "index.html"),
    `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Archetype Web UI Captures</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #111827; color: #f8fafc; }
    body { margin: 0; padding: 24px; }
    h1 { margin: 0 0 18px; font-size: 22px; }
    main { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 18px; align-items: start; }
    figure { margin: 0; border: 1px solid #374151; border-radius: 8px; background: #1f2937; overflow: hidden; }
    figcaption { padding: 10px 12px; color: #d1d5db; font-size: 13px; font-weight: 700; }
    img { display: block; width: 100%; height: auto; background: #020617; }
  </style>
</head>
<body>
  <h1>Archetype Web UI Captures</h1>
  <main>
${figures}
  </main>
</body>
</html>
`
  );
}

await fs.rm(profileDir, { recursive: true, force: true });

const chrome = spawn(process.env.CHROME_PATH, [
  "--headless=new",
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${profileDir}`,
  `--window-size=${viewportWidth},${viewportHeight}`,
  "--disable-gpu",
  "--no-default-browser-check",
  "--no-first-run",
  "about:blank",
], { stdio: ["ignore", "ignore", "ignore"] });

try {
  await waitForChrome();
  const target = await createTarget();
  const session = createSession(target.webSocketDebuggerUrl);
  await session.opened;

  const { send, once } = session;

  async function navigate(url) {
    const loaded = once("Page.loadEventFired");
    await send("Page.navigate", { url });
    await Promise.race([loaded, sleep(8000)]);
    await sleep(screenshotDelayMs);
  }

  async function waitForPageAssets() {
    const result = await send("Runtime.evaluate", {
      expression: `new Promise((resolve) => {
        const finish = () => {
          const images = Array.from(document.images || []);
          const brokenImages = images
            .filter((image) => image.complete && image.naturalWidth === 0)
            .map((image) => image.currentSrc || image.src)
            .filter(Boolean);

          resolve({
            imageCount: images.length,
            loadedImages: images.filter((image) => image.complete && image.naturalWidth > 0).length,
            brokenImageCount: brokenImages.length,
            brokenImages: brokenImages.slice(0, 8),
          });
        };

        const imageWait = new Promise((resolveImages) => {
          const pending = Array.from(document.images || []).filter((image) => !image.complete);
          if (pending.length === 0) {
            resolveImages();
            return;
          }

          let remaining = pending.length;
          const done = () => {
            remaining -= 1;
            if (remaining <= 0) {
              resolveImages();
            }
          };

          for (const image of pending) {
            image.addEventListener("load", done, { once: true });
            image.addEventListener("error", done, { once: true });
          }

          setTimeout(resolveImages, 8000);
        });

        Promise.all([
          imageWait,
          document.fonts?.ready?.catch(() => undefined) || Promise.resolve(),
        ]).then(finish);
      })`,
      awaitPromise: true,
      returnByValue: true,
    });

    return result.result?.value || {
      imageCount: 0,
      loadedImages: 0,
      brokenImageCount: 0,
      brokenImages: [],
    };
  }

  async function retryBrokenImages() {
    await send("Runtime.evaluate", {
      expression: `(() => {
        const brokenImages = Array.from(document.images || [])
          .filter((image) => image.complete && image.naturalWidth === 0);

        for (const [index, image] of brokenImages.entries()) {
          const source = image.currentSrc || image.src;
          if (!source || source.startsWith("data:")) {
            continue;
          }

          const separator = source.includes("?") ? "&" : "?";
          image.src = source + separator + "capture_retry=" + Date.now() + "_" + index;
        }

        return brokenImages.length;
      })()`,
      returnByValue: true,
    });
  }

  async function ensurePageAssets(name) {
    let status = await waitForPageAssets();

    if (status.brokenImageCount > 0) {
      console.warn(
        `Warning: ${name} had ${status.brokenImageCount} broken image(s): ${status.brokenImages.join(", ")}`
      );
      await retryBrokenImages();
      await sleep(Math.max(750, screenshotDelayMs));
      status = await waitForPageAssets();

      if (status.brokenImageCount > 0) {
        console.warn(
          `Warning: ${name} still had ${status.brokenImageCount} broken image(s) after retry: ${status.brokenImages.join(", ")}`
        );
      }
    }

    return status;
  }

  async function waitForAppData(name) {
    const result = await send("Runtime.evaluate", {
      expression: `new Promise((resolve) => {
        const captureName = ${JSON.stringify(name)};
        const startedAt = Date.now();
        const timeoutMs = 12000;
        const stableMs = 600;
        const loadingPattern = /\\bLoading\\b|Checking ranked queue status/i;
        let clearSince = null;

        const pageHasExpectedContent = (text) => {
          const normalizedText = (text || "").replace(/\\s+/g, " ").trim();
          const lowerText = normalizedText.toLowerCase();

          if (captureName === "dashboard" || captureName === "profile-menu") {
            return lowerText.includes("a tactical card battle title.") &&
              lowerText.includes("new game");
          }

          if (captureName === "dashboard-how-to") {
            return lowerText.includes("a tactical card battle title.") &&
              lowerText.includes("new game") &&
              lowerText.includes("how to play") &&
              lowerText.includes("misc rules");
          }

          if (captureName === "games") {
            return lowerText.includes("games") &&
              (lowerText.includes("ranked") || lowerText.includes("friendly"));
          }

          if (captureName === "collection") {
            return lowerText.includes("collection") &&
              lowerText.includes("your decks");
          }

          if (captureName === "new-game") {
            return lowerText.includes("new game") &&
              lowerText.includes("your deck");
          }

          if (captureName === "new-game-ai") {
            return lowerText.includes("new game") &&
              lowerText.includes("your deck") &&
              (lowerText.includes("choose ai opponent") || lowerText.includes("create pve game"));
          }

          if (captureName === "leaderboard") {
            return lowerText.includes("leaderboard") &&
              lowerText.includes("rating");
          }

          if (captureName === "friends") {
            return lowerText.includes("friends") &&
              lowerText.includes("add friend");
          }

          if (captureName === "profile" || captureName === "profile-edit") {
            return lowerText.includes("profile") &&
              lowerText.includes("account information");
          }

          if (captureName === "how-to") {
            return lowerText.includes("how to play");
          }

          if (captureName === "deck") {
            return lowerText.includes("bloodmage") &&
              lowerText.includes("total cards");
          }

          if (captureName === "deck-card-detail") {
            return lowerText.includes("bandage") &&
              lowerText.includes("cost") &&
              lowerText.includes("heal 3 health");
          }

          if (captureName === "collection-card-detail") {
            return lowerText.includes("bandage") &&
              lowerText.includes("cost");
          }

          if (captureName === "game-menu") {
            return lowerText.includes("menu") &&
              lowerText.includes("updates") &&
              lowerText.includes("concede");
          }

          if (captureName === "game-own-hero") {
            return lowerText.includes("hero power") &&
              lowerText.includes("use hero power") &&
              lowerText.includes("close");
          }

          if (captureName === "game-opponent-hero") {
            return lowerText.includes("close") &&
              !lowerText.includes("use hero power") &&
              (lowerText.includes("control") || lowerText.includes("defensive"));
          }

          if (captureName === "game-own-creature") {
            return lowerText.includes("attack") &&
              lowerText.includes("select attack target") &&
              lowerText.includes("close");
          }

          if (captureName === "game-opponent-creature") {
            return lowerText.includes("enemy creature") &&
              lowerText.includes("close") &&
              (lowerText.includes("decoy") || lowerText.includes("must be attacked first")) &&
              !lowerText.includes("select attack target");
          }

          if (
            captureName === "game-updates" ||
            captureName === "game-command-play-creature" ||
            captureName === "game-command-attack" ||
            captureName === "game-command-hero-power" ||
            captureName === "game-command-end-turn"
          ) {
            return lowerText.includes("game updates") &&
              lowerText.includes("turn");
          }

          if (captureName === "game-hand-card") {
            return lowerText.includes("card details") &&
              lowerText.includes("draw two") &&
              lowerText.includes("draw 2 cards");
          }

          if (captureName === "game-targeting-spell") {
            return lowerText.includes("select target") &&
              lowerText.includes("zap") &&
              lowerText.includes("deal 2 damage");
          }

          if (captureName === "game-hand-creature") {
            return lowerText.includes("place on board");
          }

          if (captureName === "game-placement") {
            return lowerText.includes("choose where to place this creature");
          }

          if (captureName === "game-targeting-attack") {
            return lowerText.includes("select attack target");
          }

          if (captureName === "game-mulligan") {
            return lowerText.includes("opening hand") &&
              lowerText.includes("select cards to replace");
          }

          if (captureName.startsWith("game-")) {
            return lowerText.includes("deck") &&
              lowerText.includes("hand") &&
              lowerText.includes("energy");
          }

          return normalizedText.length > 40;
        };

        const hasLoadedRankedQueueData = () => {
          if (!captureName.startsWith("ranked-queue-")) {
            return true;
          }

          const page = document.querySelector(".ranked-queue-page");
          if (!page) {
            return false;
          }

          const lines = Array.from(page.querySelectorAll("p"))
            .map((element) => (element.textContent || "").replace(/\\s+/g, " ").trim());
          const deckLine = lines.find((line) => line.startsWith("Deck:"));
          const ratingLine = lines.find((line) => line.startsWith("Your Rating:"));

          return Boolean(
            deckLine &&
            deckLine.length > "Deck:".length &&
            ratingLine &&
            /\\d+/.test(ratingLine)
          );
        };

        const tick = () => {
          const text = document.body?.innerText || "";
          const stillLoading = loadingPattern.test(text) ||
            !pageHasExpectedContent(text) ||
            !hasLoadedRankedQueueData();

          if (!stillLoading) {
            clearSince = clearSince || Date.now();
            if (Date.now() - clearSince >= stableMs) {
              requestAnimationFrame(() => {
                requestAnimationFrame(() => resolve({ settled: true, text }));
              });
              return;
            }
          } else {
            clearSince = null;
          }

          if (Date.now() - startedAt > timeoutMs) {
            resolve({ settled: false, text });
            return;
          }

          setTimeout(tick, 150);
        };

        tick();
      })`,
      awaitPromise: true,
      returnByValue: true,
    });

    if (result.exceptionDetails) {
      throw new Error(`Failed while waiting for ${name} content: ${result.exceptionDetails.text || "Runtime exception"}`);
    }

    return result.result?.value || { settled: false, text: "" };
  }

  function textPreview(text) {
    return (text || "")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 180);
  }

  const reloadSafeCaptures = new Set([
      "dashboard",
      "dashboard-how-to",
      "games",
    "collection",
    "new-game",
    "new-game-ai",
    "leaderboard",
    "friends",
    "profile",
    "how-to",
    "deck",
    "collection-card-detail",
    "game-board",
    "game-mulligan",
    "game-over-ranked",
    "ranked-queue-daily",
    "ranked-queue-rapid",
    "game-command-zap-board",
    "game-command-attack",
    "game-command-hero-power",
    "game-command-end-turn",
  ]);

  async function requireAppData(name, options = {}) {
    let status = await waitForAppData(name);
    if (status.settled) {
      return status;
    }

    if (options.allowReload) {
      const currentUrl = await send("Runtime.evaluate", {
        expression: "window.location.href",
        returnByValue: true,
      });
      const url = currentUrl.result?.value;

      if (url) {
        console.warn(`Warning: ${name} did not settle before capture; reloading once.`);
        await navigate(url);
        status = await waitForAppData(name);
        if (status.settled) {
          return status;
        }
      }
    }

    throw new Error(
      `Capture ${name} did not reach expected content. Last text: ${JSON.stringify(textPreview(status.text))}`
    );
  }

  async function clickAt(x, y) {
    await send("Input.dispatchMouseEvent", {
      type: "mousePressed",
      x,
      y,
      button: "left",
      clickCount: 1,
    });
    await send("Input.dispatchMouseEvent", {
      type: "mouseReleased",
      x,
      y,
      button: "left",
      clickCount: 1,
    });
    await sleep(screenshotDelayMs);
  }

  async function runPageInteraction(name, expression) {
    const readinessName = name.startsWith("game-") ? "game-board" : name;
    await requireAppData(readinessName, {
      allowReload: reloadSafeCaptures.has(readinessName),
    });
    await ensurePageAssets(readinessName);

    const result = await send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
    });

    if (!result.result?.value) {
      throw new Error(`Failed to open ${name} state.`);
    }

    await sleep(Math.max(250, screenshotDelayMs));
  }

  async function openProfileMenu() {
    const result = await send("Runtime.evaluate", {
      expression: `(() => {
        const button = document.querySelector('[aria-haspopup="menu"]');
        if (!button) return false;
        button.click();
        return true;
      })()`,
      returnByValue: true,
    });

    if (!result.result?.value) {
      throw new Error("Profile menu button was not found.");
    }

    await sleep(screenshotDelayMs);
  }

  async function capture(name) {
    await requireAppData(name, {
      allowReload: reloadSafeCaptures.has(name),
    });
    await ensurePageAssets(name);

    if (name === "deck") {
      await send("Runtime.evaluate", {
        expression: `(() => {
          const styleId = "archetype-play-only-deck-capture";
          if (!document.getElementById(styleId)) {
            const style = document.createElement("style");
            style.id = styleId;
            style.textContent = [
              ".deck-detail-page button[title='Increase count'],",
              ".deck-detail-page button[title='Decrease count'],",
              ".deck-detail-page button[title='Remove card'] { display: none !important; }",
              ".deck-detail-page button[title='Increase count'] { pointer-events: none !important; }",
              ".deck-detail-page .card-item > .flex.flex-col.flex-shrink-0 { display: none !important; }",
              ".deck-detail-page .card-info .font-medium { margin-left: 0.25rem !important; }",
            ].join("\\n");
            document.head.appendChild(style);
          }

          for (const panel of Array.from(document.querySelectorAll(".deck-detail-page .ui-panel"))) {
            const text = (panel.textContent || "").replace(/\\s+/g, " ").trim().toLowerCase();
            if (
              text.includes("archive deck") ||
              text.includes("edit deck") ||
              text.includes("edit cards")
            ) {
              panel.remove();
            }
          }

          return true;
        })()`,
        returnByValue: true,
      });
      await sleep(150);
    }

    if (name === "deck-card-detail") {
      await send("Runtime.evaluate", {
        expression: `(() => {
          const styleId = "archetype-play-only-deck-capture";
          if (!document.getElementById(styleId)) {
            const style = document.createElement("style");
            style.id = styleId;
            style.textContent = [
              ".deck-detail-page button[title='Increase count'],",
              ".deck-detail-page button[title='Decrease count'],",
              ".deck-detail-page button[title='Remove card'] { display: none !important; }",
              ".deck-detail-page button[title='Increase count'] { pointer-events: none !important; }",
              ".deck-detail-page .card-item > .flex.flex-col.flex-shrink-0 { display: none !important; }",
              ".deck-detail-page .card-info .font-medium { margin-left: 0.25rem !important; }",
            ].join("\\n");
            document.head.appendChild(style);
          }

          for (const panel of Array.from(document.querySelectorAll(".deck-detail-page .ui-panel"))) {
            const text = (panel.textContent || "").replace(/\\s+/g, " ").trim().toLowerCase();
            if (
              text.includes("archive deck") ||
              text.includes("edit deck") ||
              text.includes("edit cards")
            ) {
              panel.remove();
            }
          }

          return true;
        })()`,
        returnByValue: true,
      });
      await sleep(150);
    }

    if (name === "collection") {
      await send("Runtime.evaluate", {
        expression: `(() => {
          for (const element of Array.from(document.querySelectorAll(".collection-page a, .collection-page button"))) {
            const text = (element.textContent || "").replace(/\\s+/g, " ").trim().toLowerCase();
            if (text === "new deck" || text === "create your first deck") {
              const wrapper = element.parentElement;
              if (
                wrapper &&
                (wrapper.classList.contains("pt-2") ||
                  wrapper.classList.contains("text-center"))
              ) {
                wrapper.remove();
              } else {
                element.remove();
              }
            }
          }

          return true;
        })()`,
        returnByValue: true,
      });
      await sleep(150);
    }

    if (freezeAnimations) {
      await send("Runtime.evaluate", {
        expression: `(() => {
          const styleId = "archetype-visual-capture-freeze-animations";
          if (!document.getElementById(styleId)) {
            const style = document.createElement("style");
            style.id = styleId;
            style.textContent = [
              "*, *::before, *::after {",
              "  animation: none !important;",
              "  transition-duration: 0s !important;",
              "  transition-delay: 0s !important;",
              "  scroll-behavior: auto !important;",
              "  caret-color: transparent !important;",
              "}",
              ".animate-ping { opacity: 0 !important; }",
            ].join("\\n");
            document.head.appendChild(style);
          }
          return true;
        })()`,
        returnByValue: true,
      });
      await sleep(75);
    }

    const screenshot = await send("Page.captureScreenshot", {
      format: "png",
      fromSurface: true,
    });
    await fs.writeFile(path.join(outDir, `${name}.png`), Buffer.from(screenshot.data, "base64"));
  }

  async function apiFetch(pathname, options = {}) {
    return fetch(`${apiBaseUrl}${pathname}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${process.env.ACCESS_TOKEN}`,
        ...(options.headers || {}),
      },
    });
  }

  async function runManagePy(args) {
    const { stdout } = await execFileAsync(
      "docker",
      ["compose", "exec", "-T", "backend", "python", "manage.py", ...args],
      { cwd: process.cwd(), maxBuffer: 1024 * 1024 * 10 }
    );
    return stdout.replace(/\r/g, "").trim();
  }

  async function reseedLocalData(queueLadder = "daily", queueAgeSeconds = 0) {
    await runManagePy([
      "seed_archetype_dev",
      "--queue-ladder",
      queueLadder,
      "--queue-age-seconds",
      String(queueAgeSeconds),
    ]);
  }

  async function setQueueAge(ladder, ageSeconds) {
    const script = [
      "from datetime import timedelta",
      "from django.contrib.auth import get_user_model",
      "from django.utils import timezone",
      "from apps.gameplay.models import MatchmakingQueue",
      "user = get_user_model().objects.get(email='ios@devdata.local')",
      `ladder = ${JSON.stringify(ladder)}`,
      `age_seconds = ${Math.trunc(ageSeconds)}`,
      "queued_at = timezone.now() - timedelta(seconds=age_seconds)",
      "MatchmakingQueue.objects.filter(user=user, deck__title__slug='archetype', ladder_type=ladder, status=MatchmakingQueue.STATUS_QUEUED).update(created_at=queued_at, updated_at=queued_at)",
    ].join("; ");
    await runManagePy(["shell", "-c", script]);
  }

  async function resolveLatestGameId(phase = "main") {
    const output = await runManagePy([
      "shell",
      "-c",
      [
        "from django.contrib.auth import get_user_model",
        "from apps.gameplay.models import Game",
        "user = get_user_model().objects.get(email='ios@devdata.local')",
        `phase = ${JSON.stringify(phase)}`,
        "games = Game.objects.for_user(user).filter(type=Game.GAME_TYPE_PVE, status=Game.GAME_STATUS_IN_PROGRESS).order_by('-created_at')",
        "game = next((g for g in games if (g.state or {}).get('phase') == phase), None)",
        "print(game.id if game else '')",
      ].join("; "),
    ]);
    return output.split("\n").filter(Boolean).pop() || "";
  }

  async function fetchGameState(gameId) {
    const response = await apiFetch(`/gameplay/games/${gameId}/`);
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`Failed to fetch game ${gameId}: ${detail}`);
    }
    return response.json();
  }

  function cardIdBySlug(state, slug) {
    return (state.hands?.[state.viewer] || []).find((cardId) => (
      state.cards?.[cardId]?.template_slug === slug || state.cards?.[cardId]?.slug === slug
    ));
  }

  function creatureCardIdInHand(state) {
    return (state.hands?.[state.viewer] || []).find((cardId) => {
      const card = state.cards?.[cardId];
      return card?.card_type === "creature" || card?.type === "creature";
    });
  }

  function opponentSide(state) {
    return state.viewer === "side_a" ? "side_b" : "side_a";
  }

  function firstOpponentCreatureId(state) {
    const enemy = opponentSide(state);
    return state.board?.[enemy]?.[0];
  }

  function firstOwnCreatureId(state) {
    return state.board?.[state.viewer]?.[0];
  }

  function viewerHeroId(state) {
    return state.heroes?.[state.viewer]?.hero_id || state.viewer;
  }

  async function openUpdatesOverlay(captureName) {
    await runPageInteraction(captureName, `(() => {
      const update = document.querySelector('.game-update');
      if (!update) {
        return false;
      }
      const target = update.closest('.cursor-pointer') || update.parentElement;
      if (!target) {
        return false;
      }
      target.dispatchEvent(new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        view: window,
      }));
      return true;
    })()`);
  }

  async function sendGameCommand(gameId, command) {
    const wsUrl = `${wsBaseUrl}/ws/game/${gameId}/?token=${process.env.ACCESS_TOKEN}`;
    const result = await send("Runtime.evaluate", {
      expression: `new Promise((resolve) => {
        const socket = new WebSocket(${JSON.stringify(wsUrl)});
        let resolved = false;

        const finish = (value) => {
          if (resolved) return;
          resolved = true;
          try { socket.close(); } catch {}
          resolve(value);
        };

        socket.onopen = () => {
          socket.send(${JSON.stringify(JSON.stringify(command))});
        };
        socket.onmessage = (event) => {
          try {
            const payload = JSON.parse(event.data);
            if (payload.errors && payload.errors.length > 0) {
              finish({ ok: false, error: payload.errors[0].reason || JSON.stringify(payload.errors[0]) });
              return;
            }
            if (payload.state || (payload.updates && payload.updates.length > 0)) {
              setTimeout(() => finish({ ok: true }), 900);
            }
          } catch {
            setTimeout(() => finish({ ok: true }), 900);
          }
        };
        socket.onerror = () => finish({ ok: false, error: "WebSocket error" });
        setTimeout(() => finish({ ok: true, timedOut: true }), 3500);
      })`,
      awaitPromise: true,
      returnByValue: true,
    });

    const value = result.result?.value;
    if (!value?.ok) {
      throw new Error(`Failed to send game command: ${value?.error || "unknown error"}`);
    }
  }

  async function captureZapCommand() {
    await reseedLocalData("daily");
    const gameId = await resolveLatestGameId();
    const state = await fetchGameState(gameId);
    const zapId = cardIdBySlug(state, "zap");
    const targetId = firstOpponentCreatureId(state);
    if (!zapId || !targetId) {
      throw new Error("Seeded game did not contain a Zap card and opponent target.");
    }

    const gameUrl = `${baseUrl}/archetype/games/${gameId}`;
    console.log(`Capturing game-command-zap-board: ${gameUrl}`);
    await navigate(gameUrl);
    await sendGameCommand(gameId, {
      type: "cmd_play_card",
      card_id: String(zapId),
      position: 0,
      target_type: "creature",
      target_id: String(targetId),
    });
    await navigate(gameUrl);
    await capture("game-command-zap-board");
  }

  async function capturePlayCreatureCommand() {
    await reseedLocalData("daily");
    const gameId = await resolveLatestGameId();
    const state = await fetchGameState(gameId);
    const cardId = creatureCardIdInHand(state);
    const position = state.board?.[state.viewer]?.length || 0;
    if (!cardId) {
      throw new Error("Seeded game did not contain a creature card in hand.");
    }

    const gameUrl = `${baseUrl}/archetype/games/${gameId}`;
    console.log(`Capturing game-command-play-creature: ${gameUrl}`);
    await navigate(gameUrl);
    await sendGameCommand(gameId, {
      type: "cmd_play_card",
      card_id: String(cardId),
      position,
    });
    await navigate(gameUrl);
    await openUpdatesOverlay("game-command-play-creature");
    await capture("game-command-play-creature");
  }

  async function captureAttackCommand() {
    await reseedLocalData("daily");
    const gameId = await resolveLatestGameId();
    const state = await fetchGameState(gameId);
    const attackerId = firstOwnCreatureId(state);
    const targetId = firstOpponentCreatureId(state);
    if (!attackerId || !targetId) {
      throw new Error("Seeded game did not contain an attack-ready creature and opponent target.");
    }

    const gameUrl = `${baseUrl}/archetype/games/${gameId}`;
    console.log(`Capturing game-command-attack: ${gameUrl}`);
    await navigate(gameUrl);
    await sendGameCommand(gameId, {
      type: "cmd_attack",
      card_id: String(attackerId),
      target_type: "creature",
      target_id: String(targetId),
    });
    await navigate(gameUrl);
    await openUpdatesOverlay("game-command-attack");
    await capture("game-command-attack");
  }

  async function captureHeroPowerCommand() {
    await reseedLocalData("daily");
    const gameId = await resolveLatestGameId();
    const state = await fetchGameState(gameId);
    const heroId = viewerHeroId(state);
    const targetId = firstOwnCreatureId(state);
    if (!heroId || !targetId) {
      throw new Error("Seeded game did not contain a usable hero power target.");
    }

    const gameUrl = `${baseUrl}/archetype/games/${gameId}`;
    console.log(`Capturing game-command-hero-power: ${gameUrl}`);
    await navigate(gameUrl);
    await sendGameCommand(gameId, {
      type: "cmd_use_hero",
      hero_id: String(heroId),
      target_type: "creature",
      target_id: String(targetId),
    });
    await navigate(gameUrl);
    await openUpdatesOverlay("game-command-hero-power");
    await capture("game-command-hero-power");
  }

  async function captureEndTurnCommand() {
    await reseedLocalData("daily");
    const gameId = await resolveLatestGameId();
    const gameUrl = `${baseUrl}/archetype/games/${gameId}`;
    console.log(`Capturing game-command-end-turn: ${gameUrl}`);
    await navigate(gameUrl);
    await sendGameCommand(gameId, {
      type: "cmd_end_turn",
    });
    await navigate(gameUrl);
    await openUpdatesOverlay("game-command-end-turn");
    await capture("game-command-end-turn");
  }

  async function leaveQueue(ladder) {
    await apiFetch(
      `/gameplay/matchmaking/leave/archetype/?ladder_type=${encodeURIComponent(ladder)}`,
      { method: "POST" }
    ).catch(() => {});
  }

  async function ensureQueue(ladder) {
    if (!firstDeckId) {
      throw new Error("Cannot seed queue screenshot without a deck id.");
    }

    await leaveQueue("daily");
    await leaveQueue("rapid");

    const response = await apiFetch("/gameplay/matchmaking/queue/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        deck_id: Number(firstDeckId),
        ladder_type: ladder,
      }),
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`Failed to queue ${ladder}: ${detail}`);
    }

    const ageSeconds = Number(process.env.QUEUE_CAPTURE_AGE_SECONDS || 0);
    if (Number.isFinite(ageSeconds)) {
      await setQueueAge(ladder, ageSeconds);
    }
  }

  await send("Page.enable");
  await send("Runtime.enable");
  await send("Network.enable");
  await send("Emulation.setDeviceMetricsOverride", {
    width: viewportWidth,
    height: viewportHeight,
    deviceScaleFactor: 1,
    mobile: true,
  });
  await send("Emulation.setEmulatedMedia", {
    features: [{ name: "prefers-color-scheme", value: "dark" }],
  });

  await navigate(`${baseUrl}/login`);
  if (shouldCapture("login")) {
    await capture("login");
  }
  if (shouldCapture("login-signup")) {
    await runPageInteraction("login-signup", `(() => {
      const button = Array.from(document.querySelectorAll('button'))
        .find((candidate) =>
          (candidate.textContent || '')
            .replace(/\\s+/g, ' ')
            .trim()
            .toLowerCase() === 'new to drawtwo? create an account'
        );
      if (!button) return false;
      button.click();
      return true;
    })()`);
    await capture("login-signup");
  }

  await send("Runtime.evaluate", {
    expression: [
      `localStorage.setItem("accessToken", ${JSON.stringify(process.env.ACCESS_TOKEN)});`,
      `localStorage.setItem("refreshToken", ${JSON.stringify(process.env.REFRESH_TOKEN)});`,
      `localStorage.setItem("userData", ${JSON.stringify(process.env.USER_JSON)});`,
    ].join(" "),
    awaitPromise: true,
  });

  for (const [name, route] of captures) {
    if (!shouldCapture(name)) {
      continue;
    }

    const url = `${baseUrl}${route}`;
    console.log(`Capturing ${name}: ${url}`);
    await navigate(url);
    if (name === "profile-menu") {
      await openProfileMenu();
    }
    if (name === "dashboard-how-to") {
      await runPageInteraction(name, `(() => {
        const heading = Array.from(document.querySelectorAll('h1, h2, h3'))
          .find((candidate) => (candidate.textContent || '').replace(/\\s+/g, ' ').trim().toLowerCase() === 'how to play');
        if (!heading) return false;
        heading.scrollIntoView({ block: 'start', inline: 'nearest' });
        return true;
      })()`);
    }
    if (name === "profile-edit") {
      await runPageInteraction(name, `(() => {
        const button = Array.from(document.querySelectorAll('button'))
          .find((candidate) => ['edit', 'set'].includes((candidate.textContent || '').trim().toLowerCase()));
        if (!button) return false;
        button.click();
        return true;
      })()`);
    }
    if (name === "new-game-ai") {
      await requireAppData("new-game", {
        allowReload: reloadSafeCaptures.has("new-game"),
      });
      await ensurePageAssets("new-game");

      const result = await send("Runtime.evaluate", {
        expression: `(() => {
        const button = Array.from(document.querySelectorAll('button'))
          .find((candidate) => (candidate.textContent || '').replace(/\\s+/g, ' ').trim().toLowerCase().includes('vs ai'));
        if (!button) return false;
        button.click();
        return true;
      })()`,
        returnByValue: true,
      });

      if (!result.result?.value) {
        throw new Error("New Game vs AI toggle was not found.");
      }
      await sleep(Math.max(350, screenshotDelayMs));
    }
    if (name === "deck-card-detail") {
      await requireAppData("deck", {
        allowReload: reloadSafeCaptures.has("deck"),
      });
      await ensurePageAssets("deck");
      const result = await send("Runtime.evaluate", {
        expression: `(() => {
          const button = document.querySelector('.deck-detail-page .card-info button');
          if (!button) return false;
          button.click();
          return true;
        })()`,
        returnByValue: true,
      });

      if (!result.result?.value) {
        throw new Error("Deck card detail trigger was not found.");
      }
      await sleep(Math.max(350, screenshotDelayMs));
    }
    await capture(name);
  }

  for (const ladder of ["daily", "rapid"]) {
    const name = `ranked-queue-${ladder}`;
    if (!shouldCapture(name)) {
      continue;
    }

    const url = `${baseUrl}/archetype/ranked-queue?ladder_type=${ladder}`;
    console.log(`Capturing ${name}: ${url}`);
    await ensureQueue(ladder);
    await navigate(url);
    await capture(name);
  }

  const gameCapture = captures.find(([name]) => name === "game-board");
  const scriptedGameCaptures = [
    ["game-menu", `(() => {
      const menuIcon = document.querySelector('svg[aria-label="Menu"]');
      const menuButton = menuIcon?.closest('span');
      if (!menuButton) return false;
      menuButton.click();
      return true;
    })()`],
    ["game-updates", `(() => {
      for (const element of Array.from(document.querySelectorAll('.cursor-pointer'))) {
        if (element.querySelector('.game-update')) {
          element.click();
          return true;
        }
      }
      return false;
    })()`],
    ["game-hand-card", `(() => {
      const cards = Array.from(document.querySelectorAll('.hand .game-card'));
      const card = cards.find((candidate) =>
        Array.from(candidate.querySelectorAll('img')).some((image) =>
          (image.getAttribute('alt') || '') === 'Draw Two'
        )
      );
      if (!card) return false;
      card.click();
      return true;
    })()`],
    ["game-own-hero", `(() => {
      const candidates = Array.from(document.querySelectorAll('.side-a .h-full.shrink-0'));
      const hero = candidates.find((element) => element.querySelector('.cursor-pointer'));
      if (!hero) return false;
      hero.querySelector('.cursor-pointer').click();
      return true;
    })()`],
    ["game-opponent-hero", `(() => {
      const candidates = Array.from(document.querySelectorAll('.side-b .h-full.shrink-0'));
      const hero = candidates.find((element) => element.querySelector('.cursor-pointer'));
      if (!hero) return false;
      hero.querySelector('.cursor-pointer').click();
      return true;
    })()`],
    ["game-own-creature", `(() => {
      const card = document.querySelector('.viewer-board .game-card');
      if (!card) return false;
      card.click();
      return true;
    })()`],
    ["game-opponent-creature", `(() => {
      const card = document.querySelector('.opponent-board .game-card');
      if (!card) return false;
      card.click();
      return true;
    })()`],
    ["game-targeting-spell", `(() => {
      const cards = Array.from(document.querySelectorAll('.hand .game-card'));
      const card = cards.find((candidate) =>
        Array.from(candidate.querySelectorAll('img')).some((image) =>
          (image.getAttribute('alt') || '') === 'Zap'
        )
      );
      if (!card) return false;
      card.click();
      return true;
    })()`],
    ["game-hand-creature", `(async () => {
      const targetName = __CREATURE_CARD_NAME__;
      const cards = Array.from(document.querySelectorAll('.hand .game-card'));
      const namedCard = targetName
        ? cards.find((card) => Array.from(card.querySelectorAll('img')).some((image) => (image.getAttribute('alt') || '') === targetName))
        : null;
      const candidates = namedCard ? [namedCard] : cards;

      for (const card of candidates) {
        card.click();
        await new Promise((resolve) => setTimeout(resolve, 150));
        if ((document.body.innerText || '').toLowerCase().includes('place on board')) {
          return true;
        }
        const closeButton = Array.from(document.querySelectorAll('button'))
          .find((button) => (button.textContent || '').trim().toLowerCase() === 'close');
        closeButton?.click();
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
      return false;
    })()`],
    ["game-placement", `(async () => {
      const targetName = __CREATURE_CARD_NAME__;
      const cards = Array.from(document.querySelectorAll('.hand .game-card'));
      const namedCard = targetName
        ? cards.find((card) => Array.from(card.querySelectorAll('img')).some((image) => (image.getAttribute('alt') || '') === targetName))
        : null;
      const candidates = namedCard ? [namedCard] : cards;

      for (const card of candidates) {
        card.click();
        await new Promise((resolve) => setTimeout(resolve, 150));
        const placeButton = Array.from(document.querySelectorAll('button'))
          .find((button) => (button.textContent || '').trim().toLowerCase() === 'place on board');
        if (placeButton) {
          placeButton.click();
          await new Promise((resolve) => setTimeout(resolve, 150));
          return true;
        }
        const closeButton = Array.from(document.querySelectorAll('button'))
          .find((button) => (button.textContent || '').trim().toLowerCase() === 'close');
        closeButton?.click();
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
      return false;
    })()`],
    ["game-targeting-attack", `(() => {
      const card = document.querySelector('.viewer-board .game-card');
      if (!card) return false;
      card.click();
      return true;
    })()`],
  ];
  const commandCaptureNames = [
    "game-command-zap-board",
    "game-command-play-creature",
    "game-command-attack",
    "game-command-hero-power",
    "game-command-end-turn",
  ];
  const wantsGameDetailCaptures =
    shouldCapture("game-board") ||
    scriptedGameCaptures.some(([name]) => shouldCapture(name)) ||
    commandCaptureNames.some((name) => shouldCapture(name));

  if (gameCapture && wantsGameDetailCaptures) {
    const gameUrl = `${baseUrl}${gameCapture[1]}`;
    const scriptedGameId = gameCapture[1].split("/").filter(Boolean).pop();
    let creatureCardName = "";

    if (scriptedGameId) {
      const scriptedState = await fetchGameState(scriptedGameId).catch(() => null);
      const creatureCardId = scriptedState ? creatureCardIdInHand(scriptedState) : null;
      creatureCardName = creatureCardId ? (scriptedState.cards?.[creatureCardId]?.name || "") : "";
    }

    for (const [name, expression] of scriptedGameCaptures) {
      if (!shouldCapture(name)) {
        continue;
      }

      console.log(`Capturing ${name}: ${gameUrl}`);
      await navigate(gameUrl);
      await runPageInteraction(
        name,
        expression.replaceAll("__CREATURE_CARD_NAME__", JSON.stringify(creatureCardName))
      );
      await capture(name);
    }

    if (shouldCapture("game-command-zap-board")) {
      await captureZapCommand();
    }
    if (shouldCapture("game-command-play-creature")) {
      await capturePlayCreatureCommand();
    }
    if (shouldCapture("game-command-attack")) {
      await captureAttackCommand();
    }
    if (shouldCapture("game-command-hero-power")) {
      await captureHeroPowerCommand();
    }
    if (shouldCapture("game-command-end-turn")) {
      await captureEndTurnCommand();
    }
  }

  session.close();
  await writeGallery();
} finally {
  if (!chrome.killed) {
    const exited = new Promise((resolve) => {
      chrome.once("exit", resolve);
    });
    chrome.kill("SIGTERM");
    await Promise.race([exited, sleep(1500)]);
  }

  await fs.rm(profileDir, {
    recursive: true,
    force: true,
    maxRetries: 8,
    retryDelay: 150,
  });
}
NODE

echo "Saved web UI screenshots to $OUT_DIR"
echo "Open $OUT_DIR/index.html to review the capture gallery."

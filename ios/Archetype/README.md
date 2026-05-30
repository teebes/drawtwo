# Archetype iOS Prototype

Native SwiftUI prototype for the Archetype title. It talks directly to the
DrawTwo production backend at `https://drawtwo.com`.

## What Works

- Passwordless DrawTwo login using the existing email-confirm endpoint.
- Secure token storage in iOS Keychain.
- Session refresh through the existing JWT refresh endpoint.
- Archetype title loading from `/api/titles/archetype/`.
- Deck loading from `/api/collection/titles/archetype/decks/`.
- PvE opponent loading from `/api/titles/archetype/pve/`.
- Active game loading from `/api/titles/archetype/games/`.
- Practice game creation through `/api/gameplay/games/new/`.
- Game detail loading from `/api/gameplay/games/<id>/`.
- User and game WebSocket connections using the existing JWT query token.
- WebSocket requests include `Origin: https://drawtwo.com`, which the Django
  Channels `AllowedHostsOriginValidator` requires in production.
- Game socket ping to verify bidirectional WebSocket communication.

## Current Prototype Limits

- The board is not a full native gameplay implementation yet. It shows parsed
  game metadata, a raw state preview, and live WebSocket messages.
- Login uses a paste-in confirmation key because the backend currently sends a
  web login URL. Native universal links can be added later, but they require an
  Apple App Site Association file on `drawtwo.com`.
- There is no StoreKit subscription layer yet.
- There are no app icons or App Store metadata yet.

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
9. Open the email, copy the full confirmation URL or just the final key from the
   URL, return to the app, paste it into the confirmation field, and tap
   `Continue`.
10. After login, tap `Refresh` if needed, choose a deck and PvE opponent, then
    start a practice game. Open the game and tap `Ping Game Socket` to verify
    that the native app is connected to the gameplay WebSocket.

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

# AI Plumbing Implementation Notes

This document tracks the platform plumbing that prepares DrawTwo for stronger
AI agents and future model training. It complements
`docs/architecture/ai-game-engine.md`, which describes the longer-term plan.

## What Exists Now

### Agent Modules

The agent-facing backend code lives under `backend/apps/gameplay/agents/`.

- `legal.py` enumerates legal human-facing commands from a `GameState`.
- `observation.py` builds player-safe state views that hide opponent hand and
  deck order while preserving counts for existing UI code.
- `simulator.py` applies commands/effects to a copied `GameState` without
  database writes, Celery, or WebSockets.
- `hash.py` creates stable state hashes for replay verification.
- `ruleset.py` computes a `ruleset_id` from engine version, title config,
  latest heroes/cards, card traits, and trait definitions.
- `policies/` contains baseline policies. `ScriptedPolicy` preserves the
  current PvE bot behavior through the new command-level interface.

### Live Game Integration

The existing live command protocol is unchanged. Humans still submit
`cmd_play_card`, `cmd_attack`, `cmd_use_hero`, `cmd_end_turn`, `cmd_concede`,
and `cmd_mulligan`.

The built-in PvE AI now selects a `Command` first, then compiles that command
through the same `GameService.compile_cmd` path used by human players. The old
`AIMoveChooser.choose_move(...)` API still exists as a compatibility wrapper for
older tests and callers.

### Hidden Information

`filter_state_for_side` now routes through `filter_state_for_player`. Opponent
hands and both deck orders are represented by placeholder IDs so the frontend
can still count cards without receiving hidden card IDs or deck order.

Staff/superuser spectators still receive full state.

### Decision Logging

`GameAction` records command-level decisions:

- game and ruleset id
- actor side and actor kind
- turn and phase
- submitted command
- legal command list at decision time
- player-perspective observation snapshot at decision time
- pre-state hash
- outcome and error
- final winner once the live game ends

This is the base table for imitation-learning exports and replay audits.

### Deterministic Randomness

`GameState` now carries `rng_seed` and `rng_counter`. Engine randomness should
flow through `GameState.next_rng(...)` or `GameState.shuffle_in_place(...)` so
self-play and replay verification can reproduce stochastic choices.

Game creation stores the seed/counter after starting-player and deck-shuffle
randomness. Mulligan shuffle-back also uses the state RNG.

### Management Commands

Export action logs:

```bash
docker-compose exec backend python manage.py export_replays \
  --output /tmp/drawtwo-actions.jsonl
```

Useful filters:

```bash
docker-compose exec backend python manage.py export_replays \
  --title archetype \
  --actor-kind human \
  --output /tmp/archetype-human-actions.jsonl
```

Additional filters include `--game-type` and `--ladder-type`.

Run a local scripted self-play smoke test:

```bash
docker-compose exec backend python manage.py run_selfplay \
  --deck-a 1 \
  --deck-b 2 \
  --games 1
```

The self-play command uses the simulator for decisions. It creates a temporary
`Game` row only to reuse existing game-state construction, then deletes it
unless `--keep-games` is passed.

## AI Directory

The project-level `ai/` directory now contains the first local training loop.
It is mounted into the backend container by Docker Compose so scripts can run
with the normal Django/gameplay imports.

Current layout:

```text
ai/
  archetype/
  data/
  evaluation/
  models/
  selfplay/
  training/
```

See `docs/architecture/ai-training-loop.md` for the current workflow.

## Current Boundaries

This plumbing does not train a model yet. It prepares the platform by making
the game executable through stable AI-facing APIs.

The next implementation layer should add:

1. stronger legality coverage for every card/action edge case
2. replay verification that re-simulates `GameAction` rows
3. replay verification that re-simulates `GameAction` rows
4. a heuristic/search policy for Archetype
5. model-serving adapters under `backend/apps/gameplay/agents/policies/`

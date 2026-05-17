# AI Training Loop

This document tracks the first local AI training loop for Archetype. It sits on
top of the platform plumbing described in `docs/architecture/ai-plumbing.md`.

## Current Capability

We can now run an end-to-end local loop:

```text
production replay export or local self-play JSONL
-> sparse Archetype features
-> linear command-ranking policy
-> simulator evaluation against scripted/random baselines
-> more self-play JSONL
```

This is intentionally not a large neural system yet. It is a small, inspectable
baseline that proves the data shape, action scoring interface, and evaluation
flow before adding heavier ML dependencies.

## Replay Rows

Future `GameAction` rows include an `observation` snapshot:

- `side`
- `public_state`
- `legal_context`

The exporter also includes:

- `game_type`
- `ladder_type`
- `command`
- `legal_commands`
- `ruleset_id`
- `final_winner`

Older exported rows without `observation` can still be loaded, but the model can
only learn weak command-shape patterns from them. Rows with observations are the
useful training data.

## Local Scripts

The `ai/` package is mounted into the backend container at `/app/ai` in local
Docker Compose. That means the scripts can import Django gameplay code while
still living outside `backend/`.

If containers were already running before this mount existed, recreate the
backend-side containers once:

```bash
docker-compose up -d --force-recreate backend celery-worker celery-beat
```

Generate scripted self-play:

```bash
docker-compose exec backend python -m ai.selfplay.generate \
  --deck-a 1 \
  --deck-b 2 \
  --games 100 \
  --output /app/ai/runs/scripted-selfplay.jsonl
```

Train a baseline model:

```bash
docker-compose exec backend python -m ai.training.train_linear_policy \
  --input /app/ai/runs/scripted-selfplay.jsonl \
  --output /app/ai/checkpoints/archetype-linear.json
```

Evaluate the model:

```bash
docker-compose exec backend python -m ai.evaluation.evaluate_policy \
  --deck-a 1 \
  --deck-b 2 \
  --model /app/ai/checkpoints/archetype-linear.json \
  --opponent scripted \
  --games 50
```

Export production human rows:

```bash
docker-compose exec backend python manage.py export_replays \
  --title archetype \
  --actor-kind human \
  --output /tmp/archetype-human-actions.jsonl
```

## Model Shape

The first model is `linear_command_ranker_v1`.

At each decision:

1. The backend or self-play runner enumerates legal commands.
2. The feature extractor converts `(observation, candidate_command)` into sparse
   string features.
3. The model gives each legal command a score.
4. The highest-scoring legal command is selected.

The model never invents arbitrary commands, so it should stay inside the legal
action interface as long as the legal command list is correct.

## What Self-Play Means Right Now

Current self-play can generate data from:

- scripted vs scripted
- random vs scripted
- model vs scripted
- model vs model

This does not yet implement reinforcement learning. Training a model only on
its own self-play choices mostly teaches it to imitate itself. The immediate
uses are:

- stress-test the simulator
- produce enough rows to validate the training pipeline
- evaluate whether a model can execute legal games
- create baseline checkpoints for later improvement work

The next strength jump should come from a better heuristic/search teacher or a
proper policy/value reinforcement-learning loop.

## When Rules Change

Every row and live game carries a `ruleset_id`. When cards, heroes, traits, or
engine behavior changes, the `ruleset_id` should change.

Practical flow:

1. Keep old datasets and checkpoints tagged by ruleset.
2. Export/generate fresh data for the new ruleset.
3. Train a new checkpoint using mostly new-ruleset rows.
4. Optionally warm-start conceptually from old behavior later, once we have a
   neural model that supports that.
5. Promote only after evaluation on the new ruleset.

For the current linear baseline, treat a ruleset change as a reason to retrain
from current data rather than trusting old weights.

## Next Technical Steps

- Add replay verification that replays exported commands from game start.
- Add a stronger heuristic/search policy as a teacher.
- Add a neural policy/value model once the sparse baseline pipeline is stable.
- Add checkpoint metadata and promotion rules for "production bot" selection.
- Add live `ModelPolicy` integration after local evaluation is reliable.

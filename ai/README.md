# DrawTwo AI Workspace

This directory is the local home for AI training and evaluation code while the
project is still small enough to keep in one repository.

The Django app remains the source of truth for game rules:

- legal command generation lives in `backend/apps/gameplay/agents/legal.py`
- player observations live in `backend/apps/gameplay/agents/observation.py`
- deterministic simulation lives in `backend/apps/gameplay/agents/simulator.py`
- baseline policies live in `backend/apps/gameplay/agents/policies/`
- replay export starts from the `GameAction` table

AI code should import or wrap those APIs instead of reimplementing rules in this
folder. When this grows into its own repository, this directory can become the
seed for that split.

## What Exists Now

The first local training loop is deliberately dependency-free:

- `data/replays.py` streams exported JSONL decisions.
- `archetype/features.py` converts a public observation and candidate command
  into sparse features.
- `models/linear_policy.py` trains and serves a linear command ranker.
- `training/train_linear_policy.py` trains a model from replay JSONL.
- `selfplay/generate.py` generates local simulator self-play JSONL.
- `evaluation/evaluate_policy.py` evaluates a saved model against scripted or
  random baselines.

This is not the final neural engine. It is the smallest useful loop:

```text
replays/self-play rows -> train model -> evaluate model -> generate more rows
```

## Local Commands

Run these inside the backend container so the scripts can use Django's game
engine. If the backend container was already running before this directory was
mounted in `docker-compose.yml`, recreate it once with `docker-compose up -d
--force-recreate backend celery-worker celery-beat`.

```bash
docker-compose exec backend python -m ai.selfplay.generate \
  --deck-a 1 \
  --deck-b 2 \
  --games 100 \
  --output /app/ai/runs/scripted-selfplay.jsonl
```

Train a baseline:

```bash
docker-compose exec backend python -m ai.training.train_linear_policy \
  --input /app/ai/runs/scripted-selfplay.jsonl \
  --output /app/ai/checkpoints/archetype-linear.json
```

The trainer streams JSONL rows and uses a bounded shuffle buffer, so large
replay files do not need to fit in memory. Use `--limit` for smoke runs and
`--shuffle-buffer` to trade memory for better approximate shuffling.

Evaluate it:

```bash
docker-compose exec backend python -m ai.evaluation.evaluate_policy \
  --deck-a 1 \
  --deck-b 2 \
  --model /app/ai/checkpoints/archetype-linear.json \
  --opponent scripted \
  --games 50
```

Generated data belongs under `ai/runs/`, `ai/exports/`, or `ai/checkpoints/`;
those paths are ignored by git.

## Layout

```text
ai/
  archetype/
  data/
  evaluation/
  models/
  selfplay/
  training/
```

# Local AI Training Runbook

This is the concrete "what do I do right now?" checklist for getting local
Archetype training runs going while production replay data is still sparse.

## Goal

Right now the goal is not a strong AI. The goal is to make the full local loop
boring and repeatable:

```text
prod-like local decks
-> self-play rows
-> tiny baseline checkpoint
-> evaluation summary
```

The current model is a dependency-free linear command ranker. It is useful for
validating data flow and learning the workflow. It is not yet reinforcement
learning, and it will mostly imitate the data you train it on.

## Step 1: Deploy Prod Changes

Deploy the latest backend changes and run migrations on prod. This matters
because new `GameAction` rows include `observation`, which is the field that
makes human replays useful for training.

After deployment, keep playing normal PvP games when possible. Do not wait for
many human games before starting local self-play.

## Step 2: Copy Real Decklists To Local

Export a known prod deck to a slug-based manifest:

```bash
python manage.py export_deck_manifest PROD_DECK_ID \
  --output /tmp/prod-deck-PROD_DECK_ID.yaml
```

Move that YAML file to your local machine. A convenient local path is:

```text
backend/dev_data/prod-deck-PROD_DECK_ID.yaml
```

`backend/dev_data/` is ignored by git except for its placeholder files.

Import the manifest into an existing local deck ID:

```bash
docker-compose exec backend python manage.py import_deck_manifest LOCAL_DECK_ID \
  --input /app/dev_data/prod-deck-PROD_DECK_ID.yaml
```

Validate without writing:

```bash
docker-compose exec backend python manage.py import_deck_manifest LOCAL_DECK_ID \
  --input /app/dev_data/prod-deck-PROD_DECK_ID.yaml \
  --dry-run
```

The import command uses card slugs, not database IDs. It validates all card
slugs before replacing the deck and rolls back if the resulting deck is illegal
unless `--allow-invalid` is passed.

## Step 3: Find Valid Local Deck IDs

Run:

```bash
docker-compose exec backend python manage.py shell -c "
from apps.collection.models import Deck
from apps.collection.validation import validate_deck_for_play
print([
    (d.id, d.name, d.title.slug)
    for d in Deck.objects.filter(title__slug='archetype')
    if validate_deck_for_play(d) is None
])
"
```

Pick two valid same-title deck IDs. Ownership does not matter for local
self-play; the deck contents, title, hero, and optional script config matter.

## Step 4: Generate Self-Play Data

If your backend container was already running before `ai/` was mounted, recreate
backend-side containers once:

```bash
docker-compose up -d --force-recreate backend celery-worker celery-beat
```

Generate self-play rows:

```bash
docker-compose exec backend python -m ai.selfplay.generate \
  --deck-a DECK_ID_A \
  --deck-b DECK_ID_B \
  --games 100 \
  --output /app/ai/runs/archetype-scripted-selfplay.jsonl
```

This creates:

```text
ai/runs/archetype-scripted-selfplay.jsonl
```

That file is ignored by git. It contains one JSON object per decision:

- observation
- legal commands
- selected command
- pre/post state hashes
- final winner
- policy label

The self-play script creates temporary `Game` rows only to reuse game-state
construction, then deletes them unless `--keep-games` is passed. It does not
write `GameAction` rows.

## Step 5: Train A Baseline

Train from the self-play file:

```bash
docker-compose exec backend python -m ai.training.train_linear_policy \
  --input /app/ai/runs/archetype-scripted-selfplay.jsonl \
  --output /app/ai/checkpoints/archetype-linear-v1.json
```

This creates:

```text
ai/checkpoints/archetype-linear-v1.json
```

That file is ignored by git. It is the saved model checkpoint. It contains:

- `model_version`
- `feature_version`
- training metadata
- sparse feature weights

The current checkpoint is just JSON. There are no neural tensors yet.

Training does not write to the database. It reads JSONL rows and writes the
checkpoint file specified by `--output`.

## Step 6: Evaluate The Checkpoint

Evaluate against the scripted baseline:

```bash
docker-compose exec backend python -m ai.evaluation.evaluate_policy \
  --deck-a DECK_ID_A \
  --deck-b DECK_ID_B \
  --model /app/ai/checkpoints/archetype-linear-v1.json \
  --opponent scripted \
  --games 50
```

By default this prints a summary to stdout:

- wins
- losses
- draws
- win rate
- average decisions
- winners by side

If you pass `--output`, evaluation also writes decision rows:

```bash
docker-compose exec backend python -m ai.evaluation.evaluate_policy \
  --deck-a DECK_ID_A \
  --deck-b DECK_ID_B \
  --model /app/ai/checkpoints/archetype-linear-v1.json \
  --opponent scripted \
  --games 50 \
  --output /app/ai/runs/eval-archetype-linear-v1.jsonl
```

That output JSONL is also ignored by git.

## Step 7: Add Human Replay Data Later

Once prod has useful rows, export them:

```bash
python manage.py export_replays \
  --title archetype \
  --actor-kind human \
  --output /tmp/archetype-human-actions.jsonl
```

Copy the file locally, for example:

```text
ai/exports/archetype-human-actions.jsonl
```

Train from multiple inputs:

```bash
docker-compose exec backend python -m ai.training.train_linear_policy \
  --input /app/ai/exports/archetype-human-actions.jsonl \
  --input /app/ai/runs/archetype-scripted-selfplay.jsonl \
  --output /app/ai/checkpoints/archetype-linear-human-plus-selfplay.json
```

Rows without `observation` are much less useful. Prefer replay exports created
after the observation migration was deployed.

## What Gets Saved

These files are expected and ignored by git:

```text
ai/runs/*.jsonl
ai/exports/*.jsonl
ai/checkpoints/*.json
backend/dev_data/*.yaml
```

`ai/runs/*.jsonl` contains generated self-play or evaluation decisions.

`ai/exports/*.jsonl` should contain copied prod replay exports.

`ai/checkpoints/*.json` contains trained model weights and metadata.

`backend/dev_data/*.yaml` can hold copied deck manifests.

The database is only changed when you explicitly import a deck manifest into a
local deck. Self-play, training, and evaluation should not leave persistent game
or training state in the database under normal usage.

## How To Interpret Results Right Now

Do not over-read win rate yet. A model trained on scripted self-play mostly
learns scripted behavior. The useful checks are:

- self-play completes without command errors
- training uses all or most rows
- training writes a checkpoint
- evaluation can run complete games
- the model only chooses legal commands

Once this loop is reliable, the next quality step is a better teacher policy or
a real policy/value self-play training loop.

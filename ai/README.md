# DrawTwo AI Workspace

This directory is the local home for AI training and evaluation code while the
project is still small enough to keep in one repository.

The Django app remains the source of truth for game rules:

- legal command generation lives in `backend/apps/gameplay/agents/legal.py`
- player observations live in `backend/apps/gameplay/agents/observation.py`
- deterministic simulation lives in `backend/apps/gameplay/agents/simulator.py`
- baseline policies live in `backend/apps/gameplay/agents/policies/`
- replay export starts from the `GameAction` table

Future training code should import or wrap those APIs instead of reimplementing
rules in this folder. When this grows into its own repository, this directory
can become the seed for that split.

Suggested future layout:

```text
ai/
  envs/
  encoders/
  training/
  evaluation/
  models/
```


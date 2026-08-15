---
name: prod
description: Inspect, troubleshoot, and operate the live Draw Two production deployment on drawtwo.com. Use for production data inspection, logs, health checks, Django shell queries, deploy-state verification, or an explicitly requested production mutation. Do not use local production.env or localhost as evidence about the live system.
---

# Draw Two Production

Use the DigitalOcean host as the only source of truth for live production.

## Connect

Run commands through:

```sh
ssh ssh.drawtwo.com 'cd /home/teebes && docker compose -f docker-compose.production.yml --env-file production.env <command>'
```

Use the server-side `/home/teebes/production.env`. Never use the repository's
local `production.env`, a local database, or `localhost:5432` to draw conclusions
about production.

## Work Safely

1. Start with read-only inspection and resolve exact targets by stable slugs or
   other natural identifiers. Do not assume database primary keys match local
   data.
2. Treat hypothetical or example requests as non-mutating.
3. Make a production write only when the user explicitly asks to apply, change,
   update, delete, deploy, or otherwise mutate production.
4. Before a write, capture the current state needed to restore or compare the
   target. Prefer application services and validated interfaces over direct
   model updates.
5. Scope the write narrowly, use a database transaction when available, and
   avoid destructive or bulk replacement modes unless the user requests them.
6. Re-query production after a write and report the exact verified result.

For Archetype title content, use the `archetype` skill; it contains the
canonical cards/heroes inventory and guarded manifest workflow.

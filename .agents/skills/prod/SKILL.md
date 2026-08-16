---
name: prod
description: Inspect, troubleshoot, and operate the live Draw Two production deployment. Use for production data inspection, logs, health checks, Django shell queries, deploy-state verification, or an explicitly requested production mutation. Do not use repository-local configuration or localhost as evidence about the live system.
---

# Draw Two Production

Use the configured live deployment as the only source of truth for production.

## Load Private Connection Settings

Production coordinates are intentionally absent from this repository. Load them
from an operator-private JSON file by setting `DRAWTWO_PROD_CONFIG` to its path.
The file may contain the fields at the top level or under `production`:

```json
{
  "production": {
    "ssh_host": "<SSH destination>",
    "workdir": "<absolute remote deployment directory>",
    "compose_file": "<remote Compose file>",
    "env_file": "<remote environment file>",
    "backend_service": "<backend service name>"
  }
}
```

The Archetype production helper also accepts per-field overrides through
`DRAWTWO_PROD_SSH_HOST`, `DRAWTWO_PROD_WORKDIR`,
`DRAWTWO_PROD_COMPOSE_FILE`, `DRAWTWO_PROD_ENV_FILE`, and
`DRAWTWO_PROD_BACKEND_SERVICE`. Keep all values outside version control. For
general production commands, resolve the same settings and pass the destination
to `ssh` as an argument; shell-quote each value used in the remote command.

Use only the configured server-side environment file. Never use a
repository-local environment file, local database, or `localhost` to draw
conclusions about production.

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

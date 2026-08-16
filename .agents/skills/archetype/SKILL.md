---
name: archetype
description: Work on the Archetype title built on Draw Two, especially its production cards, heroes, balance, abilities, title configuration, content manifests, and current inventory. Use when asked to inspect, explain, add, edit, balance, or apply Archetype content; generate or validate Archetype YAML; determine what is currently live; or make supporting Draw Two engine, web, or iOS changes required by an Archetype design.
---

# Archetype

Treat production as the content source of truth and the repository as the source
of truth for platform behavior. Prefer content-only manifests when the current
engine supports the requested design; change Draw Two code only when needed.

## Classify the Request

- Treat examples, hypotheticals, and questions as non-mutating.
- For an inventory or "current/live" question, refresh production before
  answering.
- For a request for a manifest, draft, or proposal, generate and validate the
  artifact but do not apply it.
- Treat a direct imperative to change an existing Archetype card, hero, or title
  setting as authorization to update production unless the user says local,
  draft, proposed, manifest-only, or otherwise limits the scope. Never infer a
  deployment of Draw Two application code from a content request.
- Require explicit direction before deleting content, replacing a full title
  snapshot, deploying code, or changing user/game data.

## Load the Right Context

Read [references/production-snapshot.yaml](references/production-snapshot.yaml)
for any card or hero question. It is the complete, directly re-ingestable cache
of current production content. Check
[references/production-snapshot.meta.json](references/production-snapshot.meta.json)
for capture time and counts.

Refresh that cache when the user asks what is live, before preparing a change,
and after applying a change:

```sh
python3 .agents/skills/archetype/scripts/production.py refresh
```

Read [references/content-model.md](references/content-model.md) when a request
touches manifests, gameplay behavior, assets, tutorial coupling, or Draw Two
code. Consult the executable schemas and importer before relying on prose docs:

- `backend/apps/builder/schemas.py`
- `backend/apps/builder/services.py`
- `backend/apps/gameplay/engine/`
- `docs/card-manifests.md`

## Resolve Content Safely

Use `archetype` as the title slug and resource slugs as stable identities. Never
use a local or remembered database ID. Resolve a user-facing selector by exact
slug first, then exact case-insensitive name, and require one match. Do not
silently slugify an update; a typo can otherwise create a new resource.

Extract the complete live resource rather than rewriting it from memory:

```sh
python3 .agents/skills/archetype/scripts/production.py extract card Zap \
  --output /tmp/archetype-zap.yaml
```

Map "energy cost" and "mana cost" to the card field `cost`. Preserve every
other exported field unless the request changes it.

## Prepare a Content Change

1. Refresh the production snapshot.
2. Extract the complete target resource. For a new card or hero, model the full
   resource on the current schema and confirm the intended slug.
3. Edit only the requested fields. Use `apply_patch` for the manifest file.
4. Inspect the resource-level diff:

   ```sh
   python3 .agents/skills/archetype/scripts/production.py diff \
     /tmp/archetype-change.yaml
   ```

5. Validate the complete manifest against production without writing:

   ```sh
   python3 .agents/skills/archetype/scripts/production.py validate \
     /tmp/archetype-change.yaml
   ```

   Add `--allow-create` only when the user requested a new resource. Add
   `--allow-shape-change` only when the requested edit intentionally adds,
   removes, reorders, or replaces nested traits, actions, restrictions, or
   other list/object content.

6. If the requested output is a manifest, return the YAML and the exact diff.
   Stop without applying it.

Never send a partial card or hero resource. Current ingestion replaces omitted
traits, tags, hero restrictions, faction, spec, collectible state, and other
fields with defaults. Never use `replace_missing` for a targeted edit; it can
deactivate every omitted card or hero.

## Apply an Authorized Production Change

Use the guarded helper rather than a direct model update. It checks the cached
snapshot immediately before writing, locks the current title-content rows for
the helper's transaction, validates complete resources and their references,
refuses accidental creates, applies through `TitleService`, and returns
before/after checksums:

```sh
python3 .agents/skills/archetype/scripts/production.py apply \
  /tmp/archetype-change.yaml \
  --confirm-production archetype
```

Add `--allow-create` only for an explicitly requested new resource. Add
`--allow-shape-change` only for an explicitly requested structural addition,
removal, reorder, or replacement. A production apply is limited to one resource
by default; for an intentional multi-resource change, also pass:

```sh
--confirm-bulk-production archetype
```

Do not use that flag to apply a full snapshot. The helper does not support
deletion or `replace_missing` replacement.

Avoid applying content while someone else is editing Archetype in the builder.
The helper's row locks cover only its own transaction; an already queued
external writer can commit afterward. The immediate post-apply refresh and
resource comparison are authoritative.

If `apply` times out, loses SSH, or otherwise errors after dispatch, treat the
outcome as unknown. Refresh production and compare the affected resources before
retrying. Never retry an ambiguous production operation blindly.

After a confirmed success:

1. Refresh the production snapshot again.
2. Extract the affected resource and verify the requested values.
3. Diff the verified resource against the pre-change copy and confirm no
   unintended fields changed.
4. Report what changed, the production verification, and that existing games
   retain their copied state while newly created games use the new content.

Load production coordinates from the operator-private configuration described
in the `prod` skill. Never treat a repository-local environment file, local
database, ignored `backend/dev_data/archetypes.yaml`, or hard-coded title
primary key as production evidence.

## Decide Between Content and Platform Work

First verify that the requested traits, actions, targets, and scopes are both
schema-valid and implemented by the game engine. Schema acceptance alone does
not prove runtime support.

When platform work is needed:

1. Implement the smallest generic Draw Two capability that expresses the
   Archetype design.
2. Add backend tests for schema/import behavior and game-engine behavior.
3. Check both web and iOS clients for any presentation or interaction impact,
   following the repository's parity rule.
4. Update the intro scenario when affected slugs or behavior are referenced in
   `backend/apps/gameplay/scenario_manifests/intro_archetype.yaml`.
5. Keep the production content manifest separate from the code change. Do not
   deploy application code unless the user asks.

For visual frontend changes, first read `frontend/src/views/Styleguide.vue` and
`frontend/src/views/DesignReference.vue`, then reuse centralized classes from
`frontend/src/style.css`.

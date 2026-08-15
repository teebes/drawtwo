# Archetype Content Model

## Stable Identity and Sources

- Title: `Title(slug="archetype", is_latest=True)`.
- Card/hero identity: title-scoped `slug` on the latest template.
- Production content: `TitleService.export_snapshot_yaml()`.
- Platform behavior: repository code and tests.
- Development-only fallback: `backend/dev_data/archetypes.yaml`; never treat it
  as production truth.

The production snapshot contains title metadata, config, factions, tags, trait
overrides, all latest heroes, and all latest cards, including non-collectible
tokens. It intentionally excludes historical versions, AI decks, user/game
data, database IDs, and artwork files.

## Executable Definitions

| Concern | Source |
| --- | --- |
| Models and relationships | `backend/apps/builder/models.py` |
| Manifest schema | `backend/apps/builder/schemas.py` |
| Import/export behavior | `backend/apps/builder/services.py` |
| Authenticated builder endpoints | `backend/apps/builder/views.py` |
| Manifest examples | `docs/card-manifests.md` |
| Engine behavior | `backend/apps/gameplay/engine/` and `backend/apps/gameplay/traits.py` |
| Ruleset hashing | `backend/apps/gameplay/agents/ruleset.py` |
| Asset URL construction | `backend/apps/core/card_assets.py` |
| Intro tutorial | `backend/apps/gameplay/scenario_manifests/intro_archetype.yaml` |

Prefer schemas and services over prose documentation when they disagree.

## Ingestion Semantics

`TitleService.ingest_yaml()` updates the latest card or hero in place, preserving
its database ID and version. This keeps existing deck and collection references
attached for routine balance changes.

Card ingestion assigns every content field and then deletes and recreates all
trait rows. It also replaces tags and allowed-hero relationships. Therefore a
one-field update must start from the complete exported card resource. Hero
updates must likewise start from the complete exported hero resource.

For targeted changes:

- Use a list containing only the complete resources being changed.
- Keep `replace_missing` false.
- Wrap direct service writes in `transaction.atomic()`.
- Do not use the card-version endpoint for routine balance changes.
- Use `--allow-create` only for an intentional new slug.

## Content and Runtime Effects

Games copy title config, card templates, and hero templates into game state when
created. Existing games retain the old values. Future games receive the new
content and a newly computed ruleset ID when relevant content changes.

The schema currently recognizes more trait names than the engine necessarily
implements. Inspect handlers and tests before promising a manifest-only change.
Historically, schema-valid `armor`, trait-level `cleave`, `inspire`, and
`lifesteal` have lacked complete runtime handlers; re-check current code each
time. The `cleave` action scope is separate and implemented.

## Names and Common Fields

- User wording "energy cost" or "mana cost" maps to card `cost`.
- Creature stats are `attack` and `health`.
- Hero-power energy lives at `hero_power.cost`.
- Empty `hero_slugs` means a card is neutral; a non-empty list restricts it to
  those heroes.
- `is_collectible: false` is appropriate for summoned tokens and compensation
  cards that should not appear in deck building.

## Coupled Content

Before changing a slug or behavior, search the repository for it. In particular,
the intro scenario hard-references Archetype resources and UI examples may show
specific card/hero art or text.

Artwork is slug-addressed in R2:

- Cards: `titles/archetype/cards/<slug>.webp`
- Heroes: `titles/archetype/heroes/<slug>.webp`
- Card back: `titles/archetype/card_back.webp`
- Banner: `titles/archetype/banner.webp`

Manifest `art_url` is not persisted by the current importer. Creating or
renaming a slug can require a separate asset upload and UI/tutorial updates.

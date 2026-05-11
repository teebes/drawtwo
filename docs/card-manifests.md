# Card Manifests

Title authors can create or update game resources by pasting YAML into the title
editor's **Add / Edit Resources** section. A manifest can be one resource or a
YAML list of resources. The importer currently supports `hero`, `card`, `deck`,
and `config` resources.

Resources are applied in the order they appear, so define heroes before cards
that reference them, and define cards before decks that include them.

## Basic Card Shape

```yaml
- type: card
  card_type: creature
  slug: shield-guard
  name: Shield Guard
  description: A sturdy front-line unit.
  cost: 2
  attack: 1
  health: 4
  traits:
    - type: taunt
```

Required card fields are:

- `type: card`
- `card_type`: `creature` or `spell`
- `slug`: unique card identifier within the title
- `name`
- `cost`

Creature cards should include `attack` and `health`. Spell cards can omit them.
Optional fields include `description`, `traits`, `faction`, `art_url`,
`is_collectible`, and `hero_slugs`.

Use `is_collectible: false` for cards that should exist for gameplay effects,
such as summoned tokens, but should not be added to player decks.

## Traits And Actions

Traits are listed under `traits`. Simple traits only need a `type`:

```yaml
traits:
  - type: charge
  - type: unique
```

Triggered traits can include `actions`:

```yaml
traits:
  - type: battlecry
    actions:
      - action: damage
        amount: 2
        target: enemy
```

Common valid trait types include `charge`, `ranged`, `taunt`, `battlecry`,
`deathrattle`, `stealth`, and `unique`. Common action types include `draw`,
`damage`, `heal`, `remove`, `buff`, `summon`, `clear`, and `temp_mana_boost`.

## Hero-Specific Cards

Add `hero_slugs` to make a card available only to specific heroes in the same
title:

```yaml
- type: hero
  slug: warrior
  name: Warrior
  description: Front-line fighter.
  health: 30
  hero_power:
    name: Strike
    description: Deal 1 damage to an enemy.
    actions:
      - action: damage
        amount: 1
        target: enemy

- type: hero
  slug: mage
  name: Mage
  description: Spell-focused fighter.
  health: 30
  hero_power:
    name: Spark
    description: Deal 1 spell damage to an enemy.
    actions:
      - action: damage
        amount: 1
        target: enemy

- type: card
  card_type: spell
  slug: shield-slam
  name: Shield Slam
  description: Warrior-only removal.
  cost: 2
  hero_slugs:
    - warrior
  traits:
    - type: battlecry
      actions:
        - action: damage
          amount: 3
          target: enemy

- type: card
  card_type: spell
  slug: arcane-burst
  name: Arcane Burst
  description: Mage-only damage.
  cost: 2
  hero_slugs:
    - mage
  traits:
    - type: battlecry
      actions:
        - action: damage
          amount: 3
          target: enemy

- type: card
  card_type: creature
  slug: town-guard
  name: Town Guard
  description: Available to every hero because hero_slugs is omitted.
  cost: 1
  attack: 1
  health: 2
```

If `hero_slugs` is omitted or empty, the card is neutral and can be used by any
hero in the title. If `hero_slugs` contains one or more hero slugs, only those
heroes can add that card to decks.

The importer validates every listed hero slug. If a slug does not exist for the
title, the manifest fails and nothing is saved from that request.

## Test Decks

Deck manifests are useful for testing hero-specific cards because they exercise
the same eligibility checks used by deck building:

```yaml
- type: deck
  name: Warrior Starter
  hero: warrior
  cards:
    - card: shield-slam
      count: 2
    - card: town-guard
      count: 8

- type: deck
  name: Mage Starter
  hero: mage
  cards:
    - card: arcane-burst
      count: 2
    - card: town-guard
      count: 8
```

A deck for `mage` cannot include `shield-slam`, and a deck for `warrior` cannot
include `arcane-burst`. The collection UI should also hide cards scoped to other
heroes when adding cards to a deck.

## Updating Existing Cards

Re-ingesting a card with the same `slug` updates the latest card for that title.
Changing `hero_slugs` replaces the card's hero restriction; omitting
`hero_slugs` or setting it to an empty list makes the card neutral.

Trait entries in the resource ingestion path update or add traits by type. Use
the dedicated card edit screen when you need to remove existing traits cleanly.

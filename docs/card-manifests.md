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
`deathrattle`, `triggered`, `stealth`, and `unique`. Common action types
include `draw`, `damage`, `heal`, `remove`, `buff`, `summon`, `clear`, and
`temp_mana_boost`.

## Triggered Traits

Use `type: triggered` for abilities that fire while a creature is in play when
another game event happens. Triggered traits use a `when` condition and normal
`actions`.

Triggered abilities are stored on the creature while it is on the board. A
future silence/purge effect can disable them by removing the `triggered` trait
from that creature, the same way it would remove `deathrattle` or `taunt`.

Supported trigger events:

- `card_played`: any creature card played or spell card used
- `creature_played`: a creature card played, but not a spell card used
- `spell_used`: a spell card used, but not a creature card played
- `damage`
- `heal`
- `creature_death`
- `hero_power_used`

`source` and `target` filters are optional. Filters can include:

- `kind`: `card`, `creature`, `hero`, or `board`
- `controller`: `self`, `opponent`, or `any`
- `self: true`: the event entity must be this creature
- `exclude_self: true`: the event entity must not be this creature/card
- `card_type`: `creature` or `spell`
- `template_slug`: a specific card template slug

For triggered actions, `target: self` can be used with `buff` and `heal`.
Action amounts are usually numbers, but triggered actions can also read event
values:

```yaml
amount:
  event: damage_taken
```

Supported event amount names are `damage`, `damage_taken`, `amount`, and
`healing_done`.

Event amounts can also include `multiplier`. The resolved amount is rounded up
to the nearest integer after multiplying:

```yaml
amount:
  event: damage
  multiplier: 0.5
```

For example, `damage: 3` with `multiplier: 0.5` resolves to `2`.

### Trigger Examples

Gain +1/+1 whenever another card is played:

```yaml
traits:
  - type: triggered
    when:
      event: card_played
      source:
        controller: any
        exclude_self: true
    actions:
      - action: buff
        target: self
        attribute: attack
        amount: 1
      - action: buff
        target: self
        attribute: health
        amount: 1
```

Draw whenever another card is played:

```yaml
traits:
  - type: triggered
    when:
      event: card_played
      source:
        controller: any
        exclude_self: true
    actions:
      - action: draw
        amount: 1
```

Gain attack whenever a creature is played, but not when a spell is used:

```yaml
traits:
  - type: triggered
    when:
      event: creature_played
      source:
        controller: any
        exclude_self: true
    actions:
      - action: buff
        target: self
        attribute: attack
        amount: 1
```

Draw whenever a spell is used, but not when a creature is played:

```yaml
traits:
  - type: triggered
    when:
      event: spell_used
      source:
        controller: any
    actions:
      - action: draw
        amount: 1
```

Gain attack when your hero deals damage, including a hero power like:

```yaml
hero_power:
  name: Bloodletting
  actions:
    - action: damage
      amount: 1
      target: friendly
      scope: single
```

```yaml
traits:
  - type: triggered
    when:
      event: damage
      source:
        kind: hero
        controller: self
    actions:
      - action: buff
        target: self
        attribute: attack
        amount: 1
```

Heal your hero for the actual damage this creature took:

```yaml
traits:
  - type: triggered
    when:
      event: damage
      target:
        self: true
    actions:
      - action: heal
        target: hero
        amount:
          event: damage_taken
```

React when your hero or one of your creatures kills a creature:

```yaml
traits:
  - type: triggered
    when:
      event: creature_death
      source:
        kind: hero
        controller: self
    actions:
      - action: draw
        amount: 1

  - type: triggered
    when:
      event: creature_death
      source:
        kind: creature
        controller: self
    actions:
      - action: buff
        target: self
        attribute: health
        amount: 1
```

Gain health equal to half the damage dealt by any friendly creature, rounded up:

```yaml
traits:
  - type: triggered
    when:
      event: damage
      source:
        kind: creature
        controller: self
    actions:
      - action: buff
        target: self
        attribute: health
        amount:
          event: damage
          multiplier: 0.5
```

Use `event: damage_taken` instead of `event: damage` if overkill should only
count the actual health removed from the target.

## Hero Powers

Hero resources define a `hero_power` with a name, optional description, optional
energy `cost`, and one or more actions:

```yaml
- type: hero
  slug: warrior
  name: Warrior
  description: Front-line fighter.
  health: 30
  hero_power:
    name: Strike
    description: Deal 1 damage to an enemy.
    cost: 2
    actions:
      - action: damage
        amount: 1
        target: enemy
```

If `cost` is omitted, it defaults to `0`, so existing hero powers remain free.
When `cost` is greater than `0`, the player must have that much available
energy to use the hero power, and the energy is spent when the power is used.
Hero powers are still limited by the normal once-per-turn exhaustion behavior.

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
    cost: 2
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
    cost: 1
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

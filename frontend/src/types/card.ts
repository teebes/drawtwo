// export interface Trait {
//   slug: string
//   name: string
//   data: Record<string, any>
// }

export interface Trait {
  type: string
  actions: {}[]
  when?: {
    event: 'card_played' | 'creature_played' | 'spell_used' | 'damage' | 'heal' | 'creature_death' | 'hero_power_used'
    source?: Record<string, any>
    target?: Record<string, any>
  }
}

export interface Card {
  id: number
  slug: string
  name: string
  description?: string
  card_type: 'creature' | 'spell'
  cost: number
  attack: number
  health: number
  traits: Trait[]
  faction?: string | null
  art_url?: string | null  // For future user-uploaded art
  is_collectible?: boolean  // Defaults to true if not present
  hero_slugs?: string[]  // Empty or omitted means available to all heroes
}

export interface DeckCard extends Card {
  id: number
  count: number
}

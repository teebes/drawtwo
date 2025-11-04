// export interface Trait {
//   slug: string
//   name: string
//   data: Record<string, any>
// }

export interface Trait {
  type: string
  actions: {}[]
}

export interface Card {
  id: number
  slug: string
  name: string
  description: string
  card_type: 'creature' | 'spell'
  cost: number
  attack: number
  health: number
  traits: Trait[]
  faction?: string | null
  art_url?: string | null  // For future user-uploaded art
}

export interface DeckCard extends Card {
  id: number
  count: number
}
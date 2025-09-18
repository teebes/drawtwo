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
  card_type: 'minion' | 'spell'
  cost: number
  attack: number
  health: number
  traits: Trait[]
  faction?: string | null
}

export interface DeckCard extends Card {
  id: number
  count: number
}
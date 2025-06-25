export interface Trait {
  slug: string
  name: string
  argument: number | null
  extra_data: Record<string, any>
}

export interface Card {
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
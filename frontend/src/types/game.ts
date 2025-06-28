export type Phase = 'start' | 'refresh' | 'draw' | 'main' | 'combat' | 'end'
export type Side = 'side_a' | 'side_b'
export type Winner = 'side_a' | 'side_b' | 'none'

export interface Event {
  type: string
  player: Side
}

export interface Trait {
  slug: string
  name: string
  data: Record<string, any>
}

export interface CardInPlay {
  card_id: number
  template_slug: string
  attack: number
  health: number
  cost: number
  traits: Trait[]
}

export interface HeroInPlay {
  hero_id: number
  template_slug: string
  health: number
  name: string
}

export interface GameState {
  turn: number
  active: Side
  phase: Phase
  event_queue: Event[]
  cards: Record<number, CardInPlay>
  heroes: Record<string, HeroInPlay>
  board: Record<string, number[]>
  hands: Record<string, number[]>
  decks: Record<string, number[]>
  mana_pool: Record<string, number>
  mana_used: Record<string, number>
  winner: Winner
}
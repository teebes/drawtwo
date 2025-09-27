export type Phase = 'start' | 'refresh' | 'draw' | 'main' | 'combat' | 'end'
export type Side = 'side_a' | 'side_b'
export type Winner = 'side_a' | 'side_b' | 'none'

export interface Event {
  type: string
  player: Side
}

export type CardAction =
  | { action: 'draw'; amount: number }
  | { action: 'damage'; amount: number; target: 'hero' | 'minion' | 'enemy' }

export interface Trait {
  type: string
  actions: CardAction[]
}

export interface CardInPlay {
  card_type?: 'minion' | 'spell'
  card_id: string
  template_slug: string
  name: string
  description: string
  attack: number
  health: number
  cost: number
  traits: Trait[]
  exhausted: boolean
}

export interface HeroInPlay {
  hero_id: string
  template_slug: string
  health: number
  name: string
}

export interface GameState {
  turn: number
  active: Side
  phase: Phase
  event_queue: Event[]
  cards: Record<string, CardInPlay>
  heroes: Record<string, HeroInPlay>
  board: Record<string, string[]>
  hands: Record<string, string[]>
  decks: Record<string, string[]>
  mana_pool: Record<string, number>
  mana_used: Record<string, number>
  winner: Winner
  is_vs_ai: boolean
}
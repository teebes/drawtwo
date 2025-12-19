export type Phase = 'start' | 'refresh' | 'draw' | 'main' | 'combat' | 'end'
export type Side = 'side_a' | 'side_b'
export type Winner = 'side_a' | 'side_b' | 'none'

export interface Event {
  type: string
  player: Side
}

export type CardAction =
  | { action: 'draw'; amount: number }
  | { action: 'damage'; amount: number; target: 'hero' | 'creature' | 'enemy'; scope?: 'single' | 'cleave' | 'all'; damage_type?: 'physical' | 'spell' }
  | { action: 'heal'; amount: number; target: 'hero' | 'creature' | 'friendly'; scope?: 'single' | 'cleave' | 'all' }
  | { action: 'remove'; target: 'creature' | 'enemy'; scope?: 'single' | 'cleave' | 'all' }
  | { action: 'buff'; attribute: 'attack' | 'health'; amount: number; target: 'creature'; scope?: 'single' | 'cleave' | 'all' }


export interface Trait {
  type: string
  actions: CardAction[]
}

export interface CardInPlay {
  card_type?: 'creature' | 'spell'
  card_id: string
  template_slug: string
  name: string
  description: string
  attack: number
  health: number
  cost: number
  traits: Trait[]
  exhausted: boolean
  art_url?: string | null
}

export interface Creature {
  creature_id: string
  card_id: string
  name: string
  description: string
  attack: number
  health: number
  traits: Trait[]
  exhausted: boolean
  art_url?: string | null
}

export interface HeroPower {
  name: string
  actions: CardAction[]
  description: string
}

export interface HeroInPlay {
  hero_id: string
  template_slug: string
  health: number
  name: string
  player_name?: string | null
  description: string
  exhausted: boolean
  hero_power?: HeroPower
  art_url?: string | null
}

export interface EloChange {
  winner: {
    user_id: number
    display_name: string
    old_rating: number
    new_rating: number
    change: number
  }
  loser: {
    user_id: number
    display_name: string
    old_rating: number
    new_rating: number
    change: number
  }
}

export interface GameState {
  turn: number
  active: Side
  phase: Phase
  event_queue: Event[]
  cards: Record<string, CardInPlay>
  creatures: Record<string, Creature>
  last_creature_id: number
  heroes: Record<string, HeroInPlay>
  board: Record<string, string[]>
  hands: Record<string, string[]>
  decks: Record<string, string[]>
  mana_pool: Record<string, number>
  mana_used: Record<string, number>
  winner: Winner
  is_vs_ai: boolean
  elo_change?: EloChange
}

// Game error types - matches backend Result types
export type GameErrorType = 'outcome_rejected' | 'outcome_prevented' | 'outcome_fault'

export interface GameError {
  type: GameErrorType
  reason: string  // User-visible error message
  details?: Record<string, any>
  error_id?: string  // Only present for Fault
  effect?: any  // Only present for Fault (for debugging)
}
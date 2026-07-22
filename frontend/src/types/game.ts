export type Phase = 'mulligan' | 'start' | 'refresh' | 'draw' | 'main' | 'combat' | 'end'
export type Side = 'side_a' | 'side_b'
export type Winner = 'side_a' | 'side_b' | 'none'
export type LadderType = 'rapid' | 'daily'

export interface Event {
  type: string
  player: Side
}

export type EventAmount =
  | number
  | { event: 'amount' | 'damage' | 'damage_taken' | 'healing_done'; multiplier?: number }

export type CardAction =
  | { action: 'draw'; amount: EventAmount; spec?: Record<string, unknown> }
  | { action: 'damage'; amount: EventAmount; target: 'hero' | 'creature' | 'enemy' | 'self' | 'friendly'; scope?: 'single' | 'cleave' | 'all'; damage_type?: 'physical' | 'spell' }
  | { action: 'heal'; amount: EventAmount; target: 'hero' | 'creature' | 'friendly' | 'self'; scope?: 'single' | 'cleave' | 'all' }
  | { action: 'remove'; target: 'creature' | 'enemy'; scope?: 'single' | 'cleave' | 'all' }
  | { action: 'silence'; target: 'creature' | 'enemy'; scope?: 'single' }
  | { action: 'temp_mana_boost'; amount: EventAmount; target?: 'hero' | 'creature' | 'friendly' }
  | { action: 'summon'; target: string }
  | { action: 'clear'; target?: 'both' | 'own' | 'opponent' }
  | { action: 'buff'; attribute: 'attack' | 'health'; amount: EventAmount; target: 'hero' | 'creature' | 'friendly' | 'self'; scope?: 'single' | 'cleave' | 'all' }

export interface TriggerEntityFilter {
  kind?: 'card' | 'creature' | 'hero' | 'board'
  controller?: 'self' | 'opponent' | 'any'
  self?: boolean
  exclude_self?: boolean
  card_type?: 'creature' | 'spell'
  template_slug?: string
}

export interface TriggerCondition {
  event: 'card_played' | 'creature_played' | 'spell_used' | 'damage' | 'heal' | 'creature_death' | 'hero_power_used'
  source?: TriggerEntityFilter
  target?: TriggerEntityFilter
}

export interface Trait {
  type: string
  actions: CardAction[]
  when?: TriggerCondition
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
  faction?: string | null
  spec?: Record<string, unknown>
  tags?: string[]
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
  description?: string | null
  cost?: number
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
  mulligan_done?: Record<Side, boolean>
  mulligan_options?: Record<Side, string[]>
  decks: Record<string, string[]>
  graveyard?: Record<string, string[]>
  mana_pool: Record<string, number>
  mana_used: Record<string, number>
  winner: Winner
  is_vs_ai: boolean
  elo_change?: EloChange
  time_per_turn?: number
  turn_expires?: string | null
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

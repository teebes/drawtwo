export type CompositionGameType = 'ranked' | 'friendly'

export interface CompositionCard {
  slug: string
  count: number
  name?: string
}

export interface DeckCompositionSummary {
  id?: number
  code: string
  version?: number
  digest?: string
  manifest?: Array<{ slug: string; count: number }>
  total_cards: number
  cards?: CompositionCard[]
  url?: string
  revision?: number | {
    id?: number
    sequence?: number
    hero_slug?: string
    hero_name?: string
    source?: string
    created_at?: string
  }
  is_new?: boolean
  is_existing?: boolean
  is_preexisting?: boolean
  existing?: boolean
  preexisting?: boolean
  previously_seen?: boolean
  seen_before?: boolean
  occurrence_count?: number
  is_favorite?: boolean
}

export interface CompositionRecord {
  wins: number
  losses: number
  draws: number
  games: number
  win_rate: number | null
}

export interface CompositionHero {
  slug: string
  name: string
}

export interface CompositionHeroMatchup {
  hero: CompositionHero
  opponent_hero: CompositionHero
  global: CompositionRecord
  player: CompositionRecord | null
}

export interface CompositionStatsResponse {
  composition: DeckCompositionSummary
  game_type: CompositionGameType
  global: CompositionRecord
  player: CompositionRecord | null
  hero_matchups: CompositionHeroMatchup[]
  attribution?: {
    first_captured_at?: string | null
    captured_games?: number
    legacy_games_excluded?: boolean
  }
}

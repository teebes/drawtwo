import { defineStore } from 'pinia'
import axios from '../config/api'
import { getBaseUrl } from '../config/api'
import type { GameState, Side, CardInPlay, Creature, HeroInPlay, GameError } from '../types/game'
import { useNotificationStore } from './notifications'
import { useAuthStore } from './auth'

// WebSocket status type
type WebSocketStatus = 'disconnected' | 'connecting' | 'connected'

// Game store state interface
interface GameStoreState {
  gameState: GameState
  viewer: Side | null
  isVsAi: boolean
  loading: boolean
  error: string | null
  cardNameMap: Record<string, string>
  gameOver: {
    isGameOver: boolean
    winner: Side | null
  }
  socket: WebSocket | null
  wsStatus: WebSocketStatus

  updates: any[]
}

// Create a safe default game state so consumers can assume non-null
function createInitialGameState(): GameState {
  return {
    turn: 1,
    active: 'side_a',
    phase: 'start',
    event_queue: [],
    cards: {},
    creatures: {},
    last_creature_id: 0,
    heroes: {},
    board: { side_a: [], side_b: [] },
    hands: { side_a: [], side_b: [] },
    decks: { side_a: [], side_b: [] },
    mana_pool: { side_a: 0, side_b: 0 },
    mana_used: { side_a: 0, side_b: 0 },
    winner: 'none',
    is_vs_ai: false
  }
}

// WebSocket message type
interface WebSocketMessage {
  type: string
  [key: string]: any
}

export const useGameStore = defineStore('game', {
  state: (): GameStoreState => ({
    gameState: createInitialGameState(),
    viewer: null,
    isVsAi: false,
    loading: true,
    error: null,
    cardNameMap: {},
    gameOver: {
      isGameOver: false,
      winner: null
    },
    // WebSocket state
    socket: null,
    wsStatus: 'disconnected',
    updates: []
  }),

  getters: {
    // Helper methods
    getCard: (state) => (cardId: string): CardInPlay | undefined => {
      return state.gameState.cards[cardId]
    },

    getCreature: (state) => (creatureId: string): Creature | undefined => {
      return state.gameState.creatures[creatureId]
    },

    getHero: (state) => (heroId: string): HeroInPlay | undefined => {
      for (const side in state.gameState.heroes) {
        const hero = state.gameState.heroes[side]
        if (hero && hero.hero_id === heroId) {
          return hero
        }
      }
      return undefined
    },

    // Viewer perspective
    currentViewer: (state): Side | null => {
      return state.viewer
    },

    // Player perspective helpers
    topSide: (state): Side | null => {
      return state.viewer === 'side_a' ? 'side_b' : 'side_a'
    },

    bottomSide: (state): Side | null => {
      return state.viewer === 'side_a' ? 'side_a' : 'side_b'
    },

    // Own (current player) data
    ownSide: (state): Side | null => {
      return state.viewer === 'side_a' ? 'side_a' : 'side_b'
    },

    ownHero: (state): HeroInPlay | undefined => {
      if (!state.viewer) return undefined
      return state.gameState.heroes[state.viewer]
    },

    ownHeroName: (state): string => {
      if (!state.viewer) return ''
      const hero = state.gameState.heroes[state.viewer]
      return hero ? hero.name : ''
    },

    ownHandSize: (state): number => {
      if (!state.viewer) return 0
      return state.gameState.hands[state.viewer]?.length || 0
    },

    ownDeckSize: (state): number => {
      if (!state.viewer) return 0
      return state.gameState.decks[state.viewer]?.length || 0
    },

    ownHand: (state): string[] => {
      if (!state.viewer) return []
      return state.gameState.hands[state.viewer] || []
    },

    ownEnergy: (state): number => {
      if (!state.viewer) return 0
      const pool = state.gameState.mana_pool[state.viewer]
      const used = state.gameState.mana_used[state.viewer]
      if (pool === undefined || used === undefined) return 0
      return pool - used
    },

    ownEnergyPool: (state): number => {
      if (!state.viewer) {
        return 0
      }
      return state.gameState.mana_pool[state.viewer]
    },

    ownEnergyUsed: (state): number => {
      if (!state.viewer) {
        return 0
      }
      return state.gameState.mana_used[state.viewer]
    },

    ownBoard: (state): Creature[] => {
      if (!state.viewer) return []

      const creatureIds = state.gameState.board[state.viewer] || []
      const board: Creature[] = []

      for (const creatureId of creatureIds) {
        const creature = state.gameState.creatures[creatureId]
        if (creature) {
          board.push(creature)
        }
      }

      return board
    },

    // Opposing player data
    opposingHero: (state): HeroInPlay | null => {
      if (!state.viewer) return null
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      return state.gameState.heroes[opposingSide] ?? null
    },

    opposingHeroName: (state): string => {
      if (!state.viewer) return ''
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      const hero = state.gameState.heroes[opposingSide]
      return hero ? hero.name : ''
    },

    opposingHandSize: (state): number => {
      if (!state.viewer) return 0
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      return state.gameState.hands[opposingSide]?.length || 0
    },

    opposingDeckSize: (state): number => {
      if (!state.viewer) return 0
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      return state.gameState.decks[opposingSide]?.length || 0
    },

    opposingEnergy: (state): number => {
      if (!state.viewer) return 0
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      const pool = state.gameState.mana_pool[opposingSide]
      const used = state.gameState.mana_used[opposingSide]
      if (pool === undefined || used === undefined) return 0
      return pool - used
    },

    opposingEnergyPool: (state): number => {
      if (!state.viewer) return 0
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      return state.gameState.mana_pool[opposingSide]
    },

    opposingEnergyUsed: (state): number => {
      if (!state.viewer) return 0
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      return state.gameState.mana_used[opposingSide]
    },

    opposingBoard: (state): Creature[] => {
      if (!state.viewer) return []

      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      const creatureIds = state.gameState.board[opposingSide] || []
      const board: Creature[] = []

      for (const creatureId of creatureIds) {
        const creature = state.gameState.creatures[creatureId]
        if (creature) {
          board.push(creature)
        }
      }

      return board
    },

    // Helper methods
    isHandCardActive: (state) => (cardId: string): boolean => {
      if (!state.viewer) return false

      const card = state.gameState.cards[cardId]
      if (!card) return false

      // Calculate current energy
      const pool = state.gameState.mana_pool?.[state.viewer] || 0
      const used = state.gameState.mana_used?.[state.viewer] || 0
      const energy = pool - used

      return card.cost <= energy
    },

    canUseHero: (state): boolean => {
      if (!state.viewer) return false
      if (state.gameState.active !== state.viewer) return false
      if (state.gameState.phase !== 'main') return false

      const hero = state.gameState.heroes[state.viewer]
      if (!hero) return false

      return !hero.exhausted
    },

    // Filtered updates for display
    displayUpdates: (state): any[] => {
      return state.updates.filter((update: any) => {
        const display_types = [
          'update_draw_card',
          'update_play_card',
          'update_end_turn',
          'update_damage',
          'update_heal',
          'update_summon',
        ]

        if (display_types.includes(update.type)) {
          return true
        }

        return false
      })
    }
  },

  actions: {
    // Get notification store instance for use across actions
    getNotificationStore() {
      return useNotificationStore()
    },

    async fetchGameState(gameId: string): Promise<void> {
      try {
        this.loading = true
        this.error = null

        const response = await axios.get(`/gameplay/games/${gameId}/`)
        console.log(response.data)

        const data = response.data
        this.viewer = data.viewer
        this.gameState = data
        this.isVsAi = data.is_vs_ai

        // Build card name mapping from the game state
        this.cardNameMap = {}
        Object.values(data.cards).forEach((card: any) => {
          this.cardNameMap[card.template_slug] = card.template_slug.replace(/_/g, ' ')
            .replace(/\b\w/g, (l: string) => l.toUpperCase())
        })

      } catch (err) {
        this.error = err instanceof Error ? err.message : 'Unknown error occurred'
      } finally {
        this.loading = false
      }
    },

    connectWebSocket(gameId: string): void {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const baseUrl = getBaseUrl().replace(/^https?:/, protocol + ':')

      // Get JWT token from auth store and append as query parameter
      const authStore = useAuthStore()
      const token = authStore.accessToken
      const wsUrl = token
        ? `${baseUrl}/ws/game/${gameId}/?token=${token}`
        : `${baseUrl}/ws/game/${gameId}/`

      this.wsStatus = 'connecting'

      // WebSocket connection with JWT token in query params
      this.socket = new WebSocket(wsUrl)

      this.socket.onopen = () => {
        console.log('WebSocket connected')
        this.wsStatus = 'connected'
      }

      this.socket.onmessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data)
        this.handleWebSocketMessage(data)
      }

      this.socket.onerror = (error: Event) => {
        console.error('WebSocket error:', error)
      }

      this.socket.onclose = () => {
        console.log('WebSocket disconnected')
        this.wsStatus = 'disconnected'
      }
    },

    handleWebSocketMessage(data: any): void {
      console.log('WebSocket message:', data)

      // Handle errors first
      if (data.errors && Array.isArray(data.errors)) {
        const notificationStore = this.getNotificationStore()
        for (const error of data.errors as GameError[]) {
          // Backend always sends 'reason' for all error types (Rejected, Prevented, Fault)
          notificationStore.error(error.reason)
        }
      }

      // Update the game state
      if (data.state) {
        const oldActive = this.gameState.active
        this.gameState = data.state

        // Check for turn change to current player
        if (oldActive !== this.gameState.active &&
            this.gameState.active === this.viewer &&
            !this.gameOver.isGameOver) {
           const notificationStore = this.getNotificationStore()
           notificationStore.sendBrowserNotification("It's your turn!")
        }

        // Check if the game is over based on the state's winner field
        if (data.state.winner && data.state.winner !== 'none' && !this.gameOver.isGameOver) {
          this.setGameOver(data.state.winner)
        }
      }

      // Process any updates that came with the message
      if (data.updates && Array.isArray(data.updates)) {
        for (const update of data.updates) {
          if (update.type === 'update_game_over') {
            this.setGameOver(update.winner)
            break
          }
        }

        // Only add updates that don't already exist (based on timestamp)
        for (const update of data.updates) {
          const existingUpdate = this.updates.find(existing => existing.timestamp === update.timestamp)
          if (!existingUpdate) {
            this.updates.push(update)
          }
        }

      }
    },

    // Set game over state and handle cleanup
    setGameOver(winner: Side): void {
      if (this.gameOver.isGameOver) return // Already game over

      this.gameOver = {
        isGameOver: true,
        winner: winner
      }
      console.log(`Game over! Winner: ${winner}`)

      // Clear any pending actions or state that shouldn't persist
      this.clearGameOverState()
    },

    // Clear any state that should be reset when game over happens
    clearGameOverState(): void {
      // Any store-level state that needs clearing can be added here
      // For now, most UI state is handled by individual components
    },

    sendWebSocketMessage(message: WebSocketMessage): void {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        console.log('Sending message:', message)
        this.socket.send(JSON.stringify(message))
      }
    },

    // Game actions that components can call directly
    endTurn(): void {
      if (this.gameOver.isGameOver) return
      console.log('Ending turn')

      this.sendWebSocketMessage({
        type: 'cmd_end_turn',
      })
    },

    concedeGame(): void {
      if (this.gameOver.isGameOver) return

      this.sendWebSocketMessage({
        type: 'cmd_concede',
      })
    },

    playCard(
      cardId: string | number,
      position?: number,
      target?: { target_id: string; target_type: 'creature' | 'hero' | 'card' }
    ): void {
      if (this.gameOver.isGameOver) return

      console.log('Playing card', cardId, 'at position', position, 'with target', target)

      const message: any = {
        type: 'cmd_play_card',
        card_id: String(cardId),
      }

      if (position !== undefined && position !== null) {
        message.position = position
      }

      if (target) {
        message.target_id = target.target_id
        message.target_type = target.target_type
      }

      this.sendWebSocketMessage(message)
    },

    castSpell(
      cardId: string,
      target?: { target_id: string; target_type: 'creature' | 'hero' | 'card' }
    ): void {
      if (this.gameOver.isGameOver) return

      console.log('Casting spell card', cardId, 'with target', target)

      const message: any = {
        type: 'cmd_cast',
        card_id: String(cardId),
      }

      if (target) {
        message.target_id = target.target_id
        message.target_type = target.target_type
      }

      this.sendWebSocketMessage(message)
    },

    useCardOnCard(cardId: string, targetCardId: string): void {
      if (this.gameOver.isGameOver) return

      console.log('Using creature', cardId, 'on creature', targetCardId)

      this.sendWebSocketMessage({
        // type: 'cmd_use_card',
        type: 'cmd_attack',
        card_id: cardId,
        target_id: targetCardId,
        target_type: 'creature',
      })
    },

    useCardOnHero(cardId: string, heroId: string): void {
      if (this.gameOver.isGameOver) return

      console.log('Using creature', cardId, 'on hero', heroId)

      this.sendWebSocketMessage({
        type: 'cmd_attack',
        card_id: cardId,
        target_id: heroId,
        target_type: 'hero',
      })
    },

    useHeroOnCard(heroId: string, targetCardId: string): void {
      if (this.gameOver.isGameOver) return

      console.log('Using hero', heroId, 'on card', targetCardId)

      this.sendWebSocketMessage({
        type: 'cmd_use_hero',
        hero_id: heroId,
        target_id: targetCardId,
        target_type: 'card',
      })
    },

    useHeroOnHero(heroId: string, targetHeroId: string): void {
      if (this.gameOver.isGameOver) return

      console.log('Using hero', heroId, 'on hero', targetHeroId)

      this.sendWebSocketMessage({
        type: 'cmd_use_hero',
        hero_id: heroId,
        target_id: targetHeroId,
        target_type: 'hero',
      })
    },

    // Initialize game connection
    async connectToGame(gameId: string): Promise<void> {
      await this.fetchGameState(gameId)
      if (!this.error) {
        this.connectWebSocket(gameId)
        // Request notification permission
        this.getNotificationStore().requestBrowserPermission()
      }
    },

    // Game over utilities
    resetGameOverState(): void {
      this.gameOver = {
        isGameOver: false,
        winner: null
      }
    },

    exitGame(): void {
      this.disconnect()
      // Reset all game state
      this.gameState = createInitialGameState()
      this.viewer = null
      this.isVsAi = false
      this.loading = false
      this.error = null
      this.cardNameMap = {}
      this.resetGameOverState()
    },

    // Exit game with confirmation (for use in components)
    exitGameWithConfirmation(): boolean {
      if (confirm('Are you sure you want to exit the game?')) {
        this.exitGame()
        return true
      }
      return false
    },

    // Cleanup
    disconnect(): void {
      if (this.socket) {
        this.socket.close()
        this.socket = null
      }
      this.wsStatus = 'disconnected'
    }
  }
})
import { defineStore } from 'pinia'
import axios from '../config/api.js'
import { getBaseUrl } from '../config/api.js'
import { makeInitials } from '../utils/index'
import type { GameState, Side, CardInPlay, HeroInPlay, Winner } from '../types/game'

// WebSocket status type
type WebSocketStatus = 'disconnected' | 'connecting' | 'connected'

// Game store state interface
interface GameStoreState {
  gameState: GameState | null
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

// WebSocket message type
interface WebSocketMessage {
  type: string
  [key: string]: any
}

export const useGameStore = defineStore('game', {
  state: (): GameStoreState => ({
    gameState: null,
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
      return state.gameState?.cards[cardId]
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
      if (!state.viewer || !state.gameState) return undefined
      return state.gameState.heroes[state.viewer]
    },

    ownHeroInitials: (state): string => {
      if (!state.viewer || !state.gameState) return ''
      const hero = state.gameState.heroes[state.viewer]
      return hero ? makeInitials(hero.name) : ''
    },

    ownHandSize: (state): number => {
      if (!state.viewer || !state.gameState) return 0
      return state.gameState.hands[state.viewer]?.length || 0
    },

    ownDeckSize: (state): number => {
      if (!state.viewer || !state.gameState) return 0
      return state.gameState.decks[state.viewer]?.length || 0
    },

    ownHand: (state): string[] => {
      if (!state.viewer || !state.gameState) return []
      return state.gameState.hands[state.viewer] || []
    },

    ownEnergy: (state): number => {
      if (!state.gameState?.mana_pool || !state.gameState?.mana_used || !state.viewer) {
        return 0
      }
      const pool = state.gameState.mana_pool[state.viewer]
      const used = state.gameState.mana_used[state.viewer]
      if (pool === undefined || used === undefined) return 0
      return pool - used
    },

    ownEnergyPool: (state): number => {
      if (!state.gameState?.mana_pool || !state.viewer) {
        return 0
      }
      return state.gameState.mana_pool[state.viewer]
    },

    ownEnergyUsed: (state): number => {
      if (!state.gameState?.mana_used || !state.viewer) {
        return 0
      }
      return state.gameState.mana_used[state.viewer]
    },

    ownBoard: (state): CardInPlay[] => {
      if (!state.viewer || !state.gameState) return []

      const cards = state.gameState.board[state.viewer] || []
      const board: CardInPlay[] = []

      for (const cardId of cards) {
        const card = state.gameState.cards[cardId]
        if (card) {
          board.push(card)
        }
      }

      return board
    },

    // Opposing player data
    opposingHero: (state): HeroInPlay | null => {
      if (!state.viewer || !state.gameState) return null
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      return state.gameState.heroes[opposingSide] ?? null
    },

    opposingHeroInitials: (state): string => {
      if (!state.viewer || !state.gameState) return ''
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      const hero = state.gameState.heroes[opposingSide]
      return hero ? makeInitials(hero.name) : ''
    },

    opposingHandSize: (state): number => {
      if (!state.viewer || !state.gameState) return 0
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      return state.gameState.hands[opposingSide]?.length || 0
    },

    opposingDeckSize: (state): number => {
      if (!state.viewer || !state.gameState) return 0
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      return state.gameState.decks[opposingSide]?.length || 0
    },

    opposingEnergy: (state): number => {
      if (!state.viewer || !state.gameState?.mana_pool || !state.gameState?.mana_used) return 0
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      const pool = state.gameState.mana_pool[opposingSide]
      const used = state.gameState.mana_used[opposingSide]
      if (pool === undefined || used === undefined) return 0
      return pool - used
    },

    opposingEnergyPool: (state): number => {
      if (!state.viewer || !state.gameState?.mana_pool) return 0
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      return state.gameState.mana_pool[opposingSide]
    },

    opposingEnergyUsed: (state): number => {
      if (!state.viewer || !state.gameState?.mana_used) return 0
      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      return state.gameState.mana_used[opposingSide]
    },

    opposingBoard: (state): CardInPlay[] => {
      if (!state.viewer || !state.gameState) return []

      const opposingSide = state.viewer === 'side_a' ? 'side_b' : 'side_a'
      const cards = state.gameState.board[opposingSide] || []
      const board: CardInPlay[] = []

      for (const cardId of cards) {
        const card = state.gameState.cards[cardId]
        if (card) {
          board.push(card)
        }
      }

      return board
    },

    // Helper methods
    isHandCardActive: (state) => (cardId: string): boolean => {
      if (!state.gameState || !state.viewer) return false

      const card = state.gameState.cards[cardId]
      if (!card) return false

      // Calculate current energy
      const pool = state.gameState.mana_pool?.[state.viewer] || 0
      const used = state.gameState.mana_used?.[state.viewer] || 0
      const energy = pool - used

      return card.cost <= energy
    },

    // Filtered updates for display
    displayUpdates: (state): any[] => {
      return state.updates.filter((update: any) => {
        const display_types = ['update_draw_card', 'update_play_card', 'update_end_turn']

        if (display_types.includes(update.type)) {
          return true
        }

        return false
      })
    }
  },

  actions: {
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
      const wsUrl = `${baseUrl}/ws/game/${gameId}/`

      this.wsStatus = 'connecting'

      // WebSocket will automatically include cookies for authentication
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

      // Update the game state
      if (data.state) {
        this.gameState = data.state

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

        this.updates.push(...data.updates)

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
        type: 'end_turn_action',
      })
    },

    playCard(cardId: string | number, position: number): void {
      if (this.gameOver.isGameOver) return

      console.log('Playing card', cardId, 'at position', position)

      this.sendWebSocketMessage({
        type: 'play_card_action',
        card_id: String(cardId),
        position: position
      })
    },

    useCardOnCard(cardId: string, targetCardId: string): void {
      if (this.gameOver.isGameOver) return

      console.log('Using card', cardId, 'on card', targetCardId)

      this.sendWebSocketMessage({
        type: 'use_card_action',
        card_id: cardId,
        target_id: targetCardId,
        target_type: 'card',
      })
    },

    useCardOnHero(cardId: string, heroId: string): void {
      if (this.gameOver.isGameOver) return

      console.log('Using card', cardId, 'on hero', heroId)

      this.sendWebSocketMessage({
        type: 'use_card_action',
        card_id: cardId,
        target_id: heroId,
        target_type: 'hero',
      })
    },

    // Initialize game connection
    async connectToGame(gameId: string): Promise<void> {
      await this.fetchGameState(gameId)
      if (!this.error) {
        this.connectWebSocket(gameId)
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
      this.gameState = null
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
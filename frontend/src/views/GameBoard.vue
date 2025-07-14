<template>
  <div
    class="h-screen overflow-hidden bg-gradient-to-b from-emerald-900 via-green-800 to-emerald-900 flex flex-col">
    <!-- Loading State -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="text-white text-xl">Loading game...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="flex-1 flex items-center justify-center">
      <div class="text-red-400 text-xl">{{ error }}</div>
    </div>

    <!-- Game Board -->
    <div v-else-if="gameState" class="flex-1 flex flex-col justify-between min-h-0 max-w-7xl mx-auto w-full" @click="handleGameAreaClick">
      <!-- Game Over Overlay -->
      <div v-if="gameOver.isGameOver" class="absolute inset-0 bg-black/75 flex items-center justify-center z-50">
        <div class="bg-white dark:bg-gray-800 rounded-2xl p-8 max-w-md mx-4 text-center shadow-2xl">
          <div class="mb-6">
            <div class="text-6xl mb-4">
              {{ gameOver.winner === viewer ? '🎉' : '💀' }}
            </div>
            <h2 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              {{ gameOver.winner === viewer ? 'Victory!' : 'Defeat!' }}
            </h2>
            <p class="text-lg text-gray-600 dark:text-gray-400">
              {{ gameOver.winner === 'side_a' ? 'Side A' : 'Side B' }} wins the game!
            </p>
          </div>

          <div class="space-y-3">
            <button
              @click="$router.push('/lobby')"
              class="w-full px-4 py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
            >
              Return to Lobby
            </button>
            <button
              @click="reloadPage"
              class="w-full px-4 py-3 bg-gray-600 hover:bg-gray-700 text-white font-medium rounded-lg transition-colors"
            >
              Play Again
            </button>
          </div>
        </div>
      </div>

      <!-- Attack Animation Overlay -->
      <AttackOverlay
        v-if="attackAnimation.active"
        :from-element="attackAnimation.fromElement"
        :to-element="attackAnimation.toElement"
      />

      <!-- WebSocket Connection Status -->
      <div v-if="wsStatus !== 'connected'" class="absolute top-2 right-2 text-sm px-2 py-1 rounded"
        :class="{
          'bg-yellow-600 text-white': wsStatus === 'connecting',
          'bg-red-600 text-white': wsStatus === 'disconnected'
        }">
        {{ wsStatus === 'connecting' ? 'Connecting...' : 'Disconnected' }}
      </div>

      <!-- Side B (Top) -->
      <div class="flex-none px-4 pt-2">
        <div class="grid grid-cols-3 gap-4 items-center">
          <!-- Left: Hand Cards -->
          <div class="flex justify-start" @click.stop>
            <HandCards
              :hand-cards="gameState.hands.side_b"
              :cards="gameState.cards"
              :mana-pool="gameState.mana_pool.side_b"
              :mana-used="gameState.mana_used.side_b"
              :is-main-phase="false"
              @card-selected="handleCardSelection"
            />
          </div>

          <!-- Middle: Hero -->
          <div class="flex justify-center" @click.stop>
            <GameHero
              :hero="gameState.heroes.side_b"
              :is-targetable="isSelectingTarget && viewer === 'side_a' && !gameOver.isGameOver"
              @hero-clicked="handleHeroTarget"
            />
          </div>

          <!-- Right: Mana + Deck -->
          <div class="flex justify-end space-x-2" @click.stop>
            <ManaIndicator
              :mana-pool="gameState.mana_pool.side_b"
              :mana-used="gameState.mana_used.side_b"
            />
            <DeckIndicator :card-count="gameState.decks.side_b.length" />
          </div>
        </div>

        <!-- Side B Board (cards) -->
        <div class="pt-3 pb-2" @click.stop>
          <div class="flex justify-center">
            <div class="flex space-x-2 max-w-full overflow-x-auto">
              <BoardCard
                v-for="cardId in gameState.board.side_b.slice(0, maxCardsPerSide)"
                :key="cardId"
                :card="gameState.cards[cardId]"
                :name="getCardName(cardId)"
                :card-type="getCardType(cardId)"
                :is-targetable="isSelectingTarget && viewer === 'side_a' && !gameOver.isGameOver"
                @card-clicked="handleCardTarget"
              />
              <div v-if="gameState.board.side_b.length === 0" class="text-gray-400 text-sm py-4">
                No cards on board
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Center Battle Area -->
      <div class="flex-1 flex items-center justify-center min-h-0 relative" @click.stop>
        <div class="text-center text-white/60">
          <div class="text-lg font-bold">Turn {{ gameState.turn }}</div>
          <div class="text-sm">{{ gameState.phase }} phase</div>
          <div class="text-sm">{{ gameState.active === 'side_a' ? 'Your' : 'Opponent' }} turn</div>

          <!-- Target Selection Prompt -->
          <div v-if="isSelectingTarget" class="mt-4 bg-black/50 rounded-lg p-3">
            <div class="text-white font-bold">Select a target to attack</div>
            <button
              @click="cancelAttack"
              class="mt-2 px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>

        <!-- End Turn Button -->
        <div v-if="gameState.phase === 'main' && gameState.active === viewer && !isSelectingTarget && !gameOver.isGameOver"
             class="absolute right-4 top-1/2 transform -translate-y-1/2">
          <button
            @click="handleEndTurn"
            class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors duration-200 shadow-lg">
            End Turn
          </button>
        </div>
      </div>

      <!-- Side A (Bottom) -->
      <div class="flex-none px-4 pb-2">
        <!-- Side A Board (cards) -->
        <div class="pt-2 pb-3" @click="handleBoardClick">
          <div class="flex justify-center">
            <div class="flex space-x-2 max-w-full overflow-x-auto">
              <!-- Show placement zones when card is selected and it's our side -->
              <template v-if="selectedCard && viewer === 'side_a' && !attackingCard && !gameOver.isGameOver">
                <!-- Place at beginning if there are cards -->
                <PlacementZone v-if="gameState.board.side_a.length > 0"
                  :position="0"
                  @placement-clicked="handleCardPlacement"
                />

                <!-- Interleave cards with placement zones -->
                <template v-for="(cardId, index) in gameState.board.side_a.slice(0, maxCardsPerSide)" :key="`card-${cardId}`">
                  <BoardCard
                    :card="gameState.cards[cardId]"
                    :name="getCardName(cardId)"
                    :card-type="getCardType(cardId)"
                    @click.stop
                  />
                  <PlacementZone
                    :position="index + 1"
                    @placement-clicked="handleCardPlacement"
                  />
                </template>

                <!-- Place in center if no cards -->
                <PlacementZone v-if="gameState.board.side_a.length === 0"
                  :position="0"
                  @placement-clicked="handleCardPlacement"
                />
              </template>

              <!-- Normal view when no card selected or when attacking -->
              <template v-else>
                <BoardCard
                  v-for="cardId in gameState.board.side_a.slice(0, maxCardsPerSide)"
                  :key="cardId"
                  :card="gameState.cards[cardId]"
                  :name="getCardName(cardId)"
                  :card-type="getCardType(cardId)"
                  :is-can-attack="canCardAttack(cardId)"
                  :is-selected="attackingCard === cardId"
                  :is-attacker="attackingCard === cardId"
                  @card-clicked="handlePlayerCardClick"
                />
                <div v-if="gameState.board.side_a.length === 0" class="text-gray-400 text-sm py-4">
                  No cards on board
                </div>
              </template>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-4 items-center">
          <!-- Left: Hand Cards -->
          <div class="flex justify-start" @click.stop>
            <HandCards
              :hand-cards="gameState.hands.side_a"
              :cards="gameState.cards"
              :mana-pool="gameState.mana_pool.side_a"
              :mana-used="gameState.mana_used.side_a"
              :is-main-phase="gameState.phase === 'main' && gameState.active === 'side_a' && viewer === 'side_a' && !isSelectingTarget && !gameOver.isGameOver"
              @card-selected="handleCardSelection"
            />
          </div>


          <!-- Middle: Hero -->
          <div class="flex justify-center" @click.stop>
            <GameHero :hero="gameState.heroes.side_a" />
          </div>

          <!-- Right: Mana + Deck -->
          <div class="flex justify-end space-x-2" @click.stop>
            <ManaIndicator
              :mana-pool="gameState.mana_pool.side_a"
              :mana-used="gameState.mana_used.side_a"
            />
            <DeckIndicator :card-count="gameState.decks.side_a.length" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import axios from '../config/api.js'
import { getBaseUrl } from '../config/api.js'
import type { GameState } from '../types/game'
import GameHero from '../components/game/GameHero.vue'
import BoardCard from '../components/game/BoardCard.vue'
import DeckIndicator from '../components/game/DeckIndicator.vue'
import ManaIndicator from '../components/game/ManaIndicator.vue'
import HandCards from '../components/game/HandCards.vue'
import PlacementZone from '../components/game/PlacementZone.vue'
import AttackOverlay from '../components/game/AttackOverlay.vue'

const route = useRoute()
const gameState = ref<GameState | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const maxCardsPerSide = ref(6)

// Track selected card
const selectedCard = ref<string | null>(null)

// Track attacking card
const attackingCard = ref<string | null>(null)

// Game over state
const gameOver = ref<{
  isGameOver: boolean
  winner: 'side_a' | 'side_b' | null
}>({
  isGameOver: false,
  winner: null
})

// Attack animation state
const attackAnimation = ref<{
  active: boolean
  fromElement: HTMLElement | null
  toElement: HTMLElement | null
}>({
  active: false,
  fromElement: null,
  toElement: null
})

// WebSocket related
const socket = ref<WebSocket | null>(null)
const wsStatus = ref<'disconnected' | 'connecting' | 'connected'>('disconnected')

const viewer = ref<'side_a' | 'side_b' | null>(null)
const isVsAi = ref(false)

// Track sent actions to prevent infinite loops
const sentActions = ref<Set<string>>(new Set())

// Card name mapping - in a real app this would come from a card template API
const cardNameMap = ref<Record<string, string>>({})

const sent = ref(false);

const fetchGameState = async () => {
  try {
    const gameId = route.params.game_id
    const response = await axios.get(`/gameplay/games/${gameId}/`)

    const data = response.data
    viewer.value = data.viewer
    gameState.value = data.state;
    isVsAi.value = data.is_vs_ai;

    // Build card name mapping from the game state
    // In practice, you'd fetch card templates separately
    Object.values(data.cards).forEach((card: any) => {
      cardNameMap.value[card.template_slug] = card.template_slug.replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase())
    })

  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error occurred'
  } finally {
    loading.value = false
  }
}

const connectWebSocket = () => {
  const gameId = route.params.game_id
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const baseUrl = getBaseUrl().replace(/^https?:/, protocol + ':')
  const wsUrl = `${baseUrl}/ws/game/${gameId}/`

  wsStatus.value = 'connecting'

  // WebSocket will automatically include cookies for authentication
  socket.value = new WebSocket(wsUrl)

  socket.value.onopen = () => {
    console.log('WebSocket connected')
    wsStatus.value = 'connected'
  }

  socket.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleWebSocketMessage(data)
  }

  socket.value.onerror = (error) => {
    console.error('WebSocket error:', error)
  }

  socket.value.onclose = () => {
    console.log('WebSocket disconnected')
    wsStatus.value = 'disconnected'
    // Attempt to reconnect after 3 seconds
    return;
    setTimeout(() => {
      if (wsStatus.value === 'disconnected') {
        connectWebSocket()
      }
    }, 3000)
  }
}

const handleWebSocketMessage = (data: any) => {
  console.log('WebSocket message:', data)

  // Update the game state
  if (data.state) {
    gameState.value = data.state

    // Check if the game is over based on the state's winner field
    if (data.state.winner && data.state.winner !== 'none' && !gameOver.value.isGameOver) {
      gameOver.value = {
        isGameOver: true,
        winner: data.state.winner
      }
      console.log(`Game over detected from state! Winner: ${data.state.winner}`)
      // Cancel any ongoing actions
      selectedCard.value = null
      attackingCard.value = null
    }
  }

  // Process any updates that came with the message
  if (data.updates && Array.isArray(data.updates)) {
    for (const update of data.updates) {
      if (update.type === 'game_over_update') {
        gameOver.value = {
          isGameOver: true,
          winner: update.winner
        }
        console.log(`Game over! Winner: ${update.winner}`)
        // Cancel any ongoing actions
        selectedCard.value = null
        attackingCard.value = null
        break
      }
    }
  }

  return;

  if (data.type !== "game_updates") {
    console.log("not a game update, skipping message.");
    return;
  }

  // if (sent.value) {
  //   console.log("already sent, skipping");
  //   return;
  // }

  console.log("game updates!")



  console.log("viewer:", viewer.value)
  console.log("side:", data.state.active)

  // If we are the viewer and the game is in a start ready state,
  // start the first phase transition to draw.
  if (data.state.active === viewer.value) {
    if (data.state.phase === "start") {
      sent.value = true;
      sendWebSocketMessage({
        type: "phase_transition",
        phase: "refresh",
      })
    } else if (data.state.phase === "refresh") {
      sent.value = true;
      sendWebSocketMessage({
        type: "phase_transition",
        phase: "draw",
      })
    } else if (data.state.phase === "draw") {
      sent.value = true;
      sendWebSocketMessage({
        type: "phase_transition",
        phase: "main",
      })
    }
  }
  return;

  if (data.type === 'game_state' || data.type === 'game_update') {
    const newState = data.state || data.update?.state
    if (newState) {
      gameState.value = newState

      // Update card name mapping
      Object.values(newState.cards).forEach((card: any) => {
        cardNameMap.value[card.template_slug] = card.template_slug.replace(/_/g, ' ')
          .replace(/\b\w/g, l => l.toUpperCase())
      })

      // Handle specific update types
      if (data.update?.type === 'draw_card') {
        console.log('Card drawn!')
        // You could add visual effects or notifications here
      }
    }
  }
}

const sendWebSocketMessage = (message: any) => {
  if (socket.value && socket.value.readyState === WebSocket.OPEN) {
    socket.value.send(JSON.stringify(message))
  }
}

// Watch for side_a start phase and trigger phase transition
watch(() => gameState.value, (newState, oldState) => {
  return;

  // Handle null states
  if (!newState) {
    console.log('New state is null');
    return;
  }

  // Note: getStateDifferences function would need to be implemented if this watch logic is needed
  // For now, this watch is disabled with the early return above

  console.log('State changed');

  // Example of how to handle phase transitions based on state changes:
  /*
  if (newState && newState.active === 'side_a' && newState.phase === 'start') {
    // Create a unique key for this action
    const actionKey = `phase_transition_${newState.active}_${newState.phase}_to_draw_turn_${newState.turn}`

    // Only send if we haven't already sent this action
    if (!sentActions.value.has(actionKey)) {
      console.log('Side A is in start phase, transitioning to draw phase')
      sentActions.value.add(actionKey)

      sendWebSocketMessage({
        type: 'action',
        action: {
          type: 'phase_transition',
          phase: 'draw'
        }
      })
    }
  }

  // Clear old action keys when turn changes to prevent memory leak
  if (oldState && newState && oldState.turn !== newState.turn) {
    sentActions.value.clear()
  }
  */
}, { deep: true })

const getCardName = (cardId: string): string => {
  const card = gameState.value?.cards[cardId]
  if (!card) return 'Unknown Card'
  return cardNameMap.value[card.template_slug] || card.template_slug
}

const getCardType = (cardId: string): 'minion' | 'spell' => {
  const card = gameState.value?.cards[cardId]
  // For now, assume all cards with attack/health are minions
  return (card?.attack !== undefined && card?.health !== undefined) ? 'minion' : 'spell'
}

const handleCardSelection = (cardId: string | null) => {
  if (gameOver.value.isGameOver) return
  selectedCard.value = cardId
  // Cancel any ongoing attack when selecting a card from hand
  attackingCard.value = null
  console.log('Card selected:', cardId)
}

const handleCardPlacement = (position: number) => {
  if (gameOver.value.isGameOver) return
  if (!selectedCard.value || viewer.value !== 'side_a') return

  console.log('Playing card', selectedCard.value, 'at position', position)

  // Send websocket message to play the card
  sendWebSocketMessage({
    type: 'play_card_action',
    card_id: selectedCard.value,
    position: position
  })

  // Clear selection
  selectedCard.value = null
}

const handleBoardClick = (event: Event) => {
  // If clicking outside of a placement zone, deselect the card
  if (selectedCard.value && event.target === event.currentTarget) {
    selectedCard.value = null
  }
}

const handleGameAreaClick = (event: Event) => {
  // Deselect card when clicking in empty areas (but let child components handle their own clicks)
  if (selectedCard.value && event.target === event.currentTarget) {
    selectedCard.value = null
  }
  // Also cancel any ongoing attack
  if (attackingCard.value && event.target === event.currentTarget) {
    attackingCard.value = null
  }
}

const handleEndTurn = () => {
  if (gameOver.value.isGameOver) return
  console.log('Ending turn')

  // Send websocket message to end turn (transition to start phase)
  sendWebSocketMessage({
    type: 'end_turn_action',
  })
}

// Computed properties
const isSelectingTarget = computed(() => attackingCard.value !== null && !gameOver.value.isGameOver)

const canCardAttack = (cardId: string): boolean => {
  if (gameOver.value.isGameOver) return false
  if (!gameState.value || viewer.value !== 'side_a') return false
  if (gameState.value.phase !== 'main') return false
  if (gameState.value.active !== 'side_a') return false

  const card = gameState.value.cards[cardId]
  return card && !card.exhausted
}

// Methods for handling attacks
const handlePlayerCardClick = (cardId: string) => {
  if (gameOver.value.isGameOver) return
  if (!canCardAttack(cardId)) return

  // If we're already selecting this card, cancel the selection
  if (attackingCard.value === cardId) {
    cancelAttack()
    return
  }

  // Set this card as the attacker
  attackingCard.value = cardId
}

const handleCardTarget = async (targetCardId: string) => {
  if (gameOver.value.isGameOver) return
  if (!attackingCard.value || !gameState.value) return

  // Optimistically set the card as exhausted
  const attackerCard = gameState.value.cards[attackingCard.value]
  if (attackerCard) {
    attackerCard.exhausted = true
  }

  // Get the elements for animation
  const fromElement = document.querySelector(`[data-card-id="${attackingCard.value}"]`) as HTMLElement
  const toElement = document.querySelector(`[data-card-id="${targetCardId}"]`) as HTMLElement

  // Show attack animation
  if (fromElement && toElement) {
    attackAnimation.value = {
      active: true,
      fromElement,
      toElement
    }

    // Hide animation after it completes
    setTimeout(() => {
      attackAnimation.value = {
        active: false,
        fromElement: null,
        toElement: null
      }
    }, 600)
  }

  // Send websocket message
  sendWebSocketMessage({
    type: 'use_card_action',
    card_id: attackingCard.value,
    target_type: 'card',
    target_id: targetCardId
  })

  // Clear selection
  attackingCard.value = null
}

const handleHeroTarget = async (heroId: string) => {
  if (gameOver.value.isGameOver) return
  if (!attackingCard.value || !gameState.value) return

  // Optimistically set the card as exhausted
  const attackerCard = gameState.value.cards[attackingCard.value]
  if (attackerCard) {
    attackerCard.exhausted = true
  }

  // Get the elements for animation
  const fromElement = document.querySelector(`[data-card-id="${attackingCard.value}"]`) as HTMLElement
  const toElement = document.querySelector(`[data-hero-id="${heroId}"]`) as HTMLElement

  // Show attack animation
  if (fromElement && toElement) {
    attackAnimation.value = {
      active: true,
      fromElement,
      toElement
    }

    // Hide animation after it completes
    setTimeout(() => {
      attackAnimation.value = {
        active: false,
        fromElement: null,
        toElement: null
      }
    }, 600)
  }

  // Send websocket message
  sendWebSocketMessage({
    type: 'use_card_action',
    card_id: attackingCard.value,
    target_type: 'hero',
    target_id: heroId
  })

  // Clear selection
  attackingCard.value = null
}

const cancelAttack = () => {
  attackingCard.value = null
}

const reloadPage = () => {
  window.location.reload()
}

onMounted(() => {
  fetchGameState().then(() => {
    if (!error.value) {
      connectWebSocket()
    }
  })
})

onUnmounted(() => {
  if (socket.value) {
    socket.value.close()
  }
})
</script>

<style scoped>
/* Custom scrollbar for horizontal card overflow */
.overflow-x-auto::-webkit-scrollbar {
  height: 4px;
}

.overflow-x-auto::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

.overflow-x-auto::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
}

.overflow-x-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}
</style>
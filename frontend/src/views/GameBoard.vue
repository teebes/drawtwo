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
            <GameHero :hero="gameState.heroes.side_b" />
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
              <BoardCard v-for="cardId in gameState.board.side_b.slice(0, maxCardsPerSide)" :key="cardId"
                :card="gameState.cards[cardId]" :name="getCardName(cardId)" :card-type="getCardType(cardId)" />
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
        </div>

        <!-- End Turn Button -->
        <div v-if="gameState.phase === 'main' && gameState.active === viewer"
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
              <template v-if="selectedCard && viewer === 'side_a'">
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

              <!-- Normal view when no card selected -->
              <template v-else>
                <BoardCard v-for="cardId in gameState.board.side_a.slice(0, maxCardsPerSide)" :key="cardId"
                  :card="gameState.cards[cardId]" :name="getCardName(cardId)" :card-type="getCardType(cardId)" />
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
              :is-main-phase="gameState.phase === 'main' && gameState.active === 'side_a' && viewer === 'side_a'"
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
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import axios from '../config/api.js'
import type { GameState } from '../types/game'
import GameHero from '../components/game/GameHero.vue'
import BoardCard from '../components/game/BoardCard.vue'
import DeckIndicator from '../components/game/DeckIndicator.vue'
import ManaIndicator from '../components/game/ManaIndicator.vue'
import HandCards from '../components/game/HandCards.vue'
import PlacementZone from '../components/game/PlacementZone.vue'

const route = useRoute()
const gameState = ref<GameState | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const maxCardsPerSide = ref(6)

// Track selected card
const selectedCard = ref<string | null>(null)

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
  // Match the API configuration pattern
  const wsUrl = `${protocol}://localhost:8000/ws/game/${gameId}/`

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

  gameState.value = data.state;
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
  selectedCard.value = cardId
  console.log('Card selected:', cardId)
}

const handleCardPlacement = (position: number) => {
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
}

const handleEndTurn = () => {
  console.log('Ending turn')

  // Send websocket message to end turn (transition to start phase)
  sendWebSocketMessage({
    type: 'end_turn_action',
  })
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
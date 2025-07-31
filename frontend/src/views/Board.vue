<template>
    <div class="min-h-screen flex flex-row justify-center" v-if="!loading">

        <!-- Normal Mode -->
        <main v-if="!overlay" class="board flex-1 flex flex-col max-w-md w-full border-r border-l border-gray-700">

            <!-- Opponent Side -->
            <div class="side-b flex-1 flex flex-col">

                <!-- Header -->
                 <div class="h-24 flex flex-row justify-between border-b border-gray-700">
                    <!-- Enemy Hero-->
                    <div class="w-24 flex flex-col items-center justify-center border-r border-gray-700" :class="{ 'bg-yellow-500/20': gameState?.active === top_side }">
                        <div class="">{{ opposing_hero_initials }}</div>
                        <div class="">{{ opposing_hero?.health }}</div>
                    </div>

                    <div class="flex flex-1 flex-row items-center justify-center space-x-4">
                        <div>{{ gameState?.phase }}</div>
                        <!-- <div>{{ gameState?.active }}</div> -->
                    </div>

                    <!-- Menu -->
                    <div class="w-24 flex justify-center items-center text-center border-l border-gray-700">
                        <span class="inline-block">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-label="Menu" xmlns="http://www.w3.org/2000/svg">
                                <rect y="5" width="24" height="2" rx="1" fill="currentColor"/>
                                <rect y="11" width="24" height="2" rx="1" fill="currentColor"/>
                                <rect y="17" width="24" height="2" rx="1" fill="currentColor"/>
                            </svg>
                        </span>
                    </div>
                 </div>

                 <!-- Stats -->
                 <div class="flex flex-row justify-around border-b border-gray-700 p-2">
                    <div class="flex flex-col text-center">
                        <div>Deck</div>
                        <div>{{ opposing_deck_size }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div>Hand</div>
                        <div>{{ opposing_hand_size }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div>Energy</div>
                        <div>{{ opposing_energy }}</div>
                    </div>
                 </div>

                 <!-- Opponent Board -->
                 <div class="opponent-board flex-1 flex flex-row bg-gray-800 items-center">
                    <div class="lane flex flex-row w-full h-24 justify-center overflow-x-auto">
                        <div v-for="card_id in opposing_board" :key="card_id" class="p-1">
                            <GameCard v-if="get_card(card_id)"
                                      class="flex-grow-0"
                                      :card="get_card(card_id)!"
                                      compact in_lane/>
                        </div>
                    </div>
                 </div>
            </div>

            <!-- Mid Section -->
            <div class="flex flex-row-reverse border-gray-700 border-t border-b">
                <GameButton
                    variant="secondary"
                    class="m-2"
                    @click="handleEndTurn">End Turn</GameButton>
            </div>

            <!-- Viewer Side-->
            <div class="side-a flex-1 flex flex-col">
                <!-- Viewer Board-->
                <div class="viewer-board flex-1 flex flex-row bg-gray-800 items-center">
                    <div class="lane flex flex-row w-full h-24 justify-center overflow-x-auto">
                        <div v-for="card_id in own_board" :key="card_id" class="p-1">
                            <GameCard v-if="get_card(card_id)"
                                      class="flex-grow-0"
                                      :card="get_card(card_id)!"
                                      compact in_lane/>
                        </div>
                    </div>
                 </div>

                <!-- Stats -->
                 <div class="flex flex-row justify-around border-t border-gray-700 p-2">
                    <div class="flex flex-col text-center">
                        <div>Deck</div>
                        <div>{{ own_deck_size }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div>Hand</div>
                        <div>{{ own_hand_size }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div>Energy</div>
                        <div>{{ own_energy }}</div>
                    </div>
                 </div>

                <!-- Footer -->
                <div class="h-24 flex flex-row border-t border-gray-700">
                    <!-- Viewer Hero -->
                    <div class="hero w-24 h-full border-r border-gray-700 flex flex-col items-center justify-center" :class="{ 'bg-yellow-500/20': gameState?.active === bottom_side }">
                        <div class="hero-name">{{ own_hero_initials }}</div>
                        <div class="hero-health">{{ own_hero?.health }}</div>
                    </div>

                    <!-- Hand -->
                    <div class="hand overflow-x-auto flex flex-row">
                        <div v-for="card_id in own_hand" :key="card_id" class="p-1">
                            <GameCard v-if="get_card(card_id)"
                                      class="flex-grow-0"
                                      :card="get_card(card_id)!"
                                      :active="isHandCardActive(card_id)"
                                      @click="handleSelectHandCard(card_id)"
                                      compact />
                        </div>
                    </div>
                </div>
            </div>

        </main>

        <!-- Overlay Mode -->
         <main v-else class="board flex-1 flex flex-col max-w-md w-full border-r border-l border-gray-700">
            <!-- Header -->
            <div class="flex flex-row w-full h-24 border-b border-gray-700 items-center">
                <!-- Display Text -->
                <div class="flex-1 text-center text-gray-400">{{ overlay_text }}</div>

                <!-- Close Button-->
                <div
                  class="w-24 h-full flex items-center justify-center cursor-pointer group relative border-l border-gray-700"
                  @click="overlay = null"
                  title="Click to close overlay"
                >
                  <span
                    class="text-6xl text-gray-500 group-hover:text-gray-100 select-none pointer-events-none"
                    style="line-height: 1;"
                  >&times;</span>
                  <span class="sr-only">Close overlay</span>
                </div>
            </div>

            <!-- Hand Card Board Selection Overlay-->
            <HandCardPlacementOverlay
                v-if="overlay == 'select_hand_card'"
                :game-state="gameState"
                :selected-hand-card="selected_hand_card"
                :own-board="own_board"
                :own-energy="own_energy"
                @card-placement="handleCardPlacement"
                @close-overlay="overlay = null"
            />


         </main>

        <!-- -->
    </div>

    <!-- Loading Screen -->
    <div class="min-h-screen flex flex-row justify-center" v-else>
        <div class="flex flex-col items-center justify-center">
            <div class="text-2xl font-bold">Loading...</div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { watch, computed, ref, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { GameState } from '../types/game'
import { useTitleStore } from '../stores/title.js'
import { getBaseUrl } from '../config/api.js'
import axios from '../config/api.js'
import { makeInitials } from '../utils'

import GameCard from '../components/game/GameCard.vue'
import GameButton from '../components/ui/GameButton.vue'
import HandCardPlacementOverlay from '../components/game/board/HandCardPlacementOverlay.vue'

const route = useRoute()
const router = useRouter()
const titleStore = useTitleStore()

const loading = ref(true)
const mode = ref<'normal' | 'select_hand_card'>('normal')
const gameState = ref<GameState | null>(null)
const viewer = ref<'side_a' | 'side_b' | null>(null)
const isVsAi = ref(false)
const error = ref<string | null>(null)
const cardNameMap = ref<Record<string, string>>({})
const gameOver = ref<{
  isGameOver: boolean
  winner: 'side_a' | 'side_b' | null
}>({
  isGameOver: false,
  winner: null
})
const selected_hand_card = ref<string | null>(null)

const overlay = ref<'select_hand_card' | null>(null)
const overlay_text = ref<string | null>(null)

// WebSocket related
const socket = ref<WebSocket | null>(null)
const wsStatus = ref<'disconnected' | 'connecting' | 'connected'>('disconnected')


const title = computed(() => titleStore.currentTitle)

const top_side = computed(() => { return viewer.value === 'side_a' ? 'side_b' : 'side_a' })
const bottom_side = computed(() => { return viewer.value === 'side_a' ? 'side_a' : 'side_b' })


const get_card = (card_id: string) => {
    return gameState.value?.cards[card_id]
}

const isHandCardActive = (card_id: string) => {
    // An active hand card is one that can be played, meaning that its cost
    // is less than the current energy.
    const card = get_card(card_id)
    if (!card) return false
    if (card.cost <= own_energy.value) return true
    return false
}

const handleEndTurn = () => {
    if (gameOver.value.isGameOver) return
    console.log('Ending turn')

    // Send websocket message to end turn (transition to start phase)
    sendWebSocketMessage({
        type: 'end_turn_action',
    })
}

const handleSelectHandCard = (card_id: string) => {
    overlay.value = 'select_hand_card'
    overlay_text.value = "Select the card's location on the board"
    selected_hand_card.value = card_id
}

const handleCardPlacement = (cardId: string, position: number) => {
    if (gameOver.value.isGameOver) return

    console.log('Playing card', cardId, 'at position', position)

    // Send websocket message to play the card
    sendWebSocketMessage({
        type: 'play_card_action',
        card_id: cardId,
        position: position
    })

    // Clear selection and close overlay
    selected_hand_card.value = null
    overlay.value = null
    overlay_text.value = null
}


/*
    Own Data

    We want whoever is viewing their game to be at the bottom. Determine whether
    the viewer is side_a or side_b.
*/
const own_side = computed(() => { return viewer.value === 'side_a' ? 'side_a' : 'side_b' })
const own_hero = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.heroes.side_a
    } else {
        return gameState.value?.heroes.side_b
    }
})
const own_hero_initials = computed(() => {
    if (own_hero.value) {
        return makeInitials(own_hero.value.name)
    }
    return ''
})
const own_hand_size = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.hands.side_a.length
    } else {
        return gameState.value?.hands.side_b.length
    }
})
const own_deck_size = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.decks.side_a.length
    } else {
        return gameState.value?.decks.side_b.length
    }
})
const own_hand = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.hands.side_a
    } else {
        return gameState.value?.hands.side_b
    }
})
const own_energy = computed(() => {
    if (!gameState.value || !gameState.value.mana_pool || !gameState.value.mana_used || !viewer.value) {
        return 0
    }
    if (viewer.value === 'side_a') {
        const pool = gameState.value.mana_pool.side_a
        const used = gameState.value.mana_used.side_a
        if (pool === undefined || used === undefined) return 0
        return pool - used
    } else {
        const pool = gameState.value.mana_pool.side_b
        const used = gameState.value.mana_used.side_b
        if (pool === undefined || used === undefined) return 0
        return pool - used
    }
})
const own_board = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.board.side_a
    } else {
        return gameState.value?.board.side_b
    }
})

/*
    Opponent Data

    We want whoever is viewing their game to be at the bottom. Because of this,
    we have to use computed data to determine which side is on top and fetch the
    appropriate data.
*/
const opposing_hero = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.heroes.side_b
    } else {
        return gameState.value?.heroes.side_a
    }
})
const opposing_hero_initials = computed(() => {
    if (opposing_hero.value) {
        return makeInitials(opposing_hero.value.name)
    }
    return ''
})
const opposing_hand_size = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.hands.side_b.length
    } else {
        return gameState.value?.hands.side_a.length
    }
})
const opposing_deck_size = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.decks.side_b.length
    } else {
        return gameState.value?.decks.side_a.length
    }
})
const opposing_energy = computed(() => {
    if (viewer.value === 'side_a') {
        const pool = gameState.value?.mana_pool.side_b
        const used = gameState.value?.mana_used.side_b
        if (pool === undefined || used === undefined) return 0
        return pool - used
    } else {
        const pool = gameState.value?.mana_pool.side_a
        const used = gameState.value?.mana_used.side_a
        if (pool === undefined || used === undefined) return 0
        return pool - used
    }
})
const opposing_board = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.board.side_b
    } else {
        return gameState.value?.board.side_a
    }
})


const fetchGameState = async () => {
  try {
    const gameId = route.params.game_id
    const response = await axios.get(`/gameplay/games/${gameId}/`)

    console.log(response.data)

    const data = response.data
    viewer.value = data.viewer
    gameState.value = data;
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
                break
            }
        }
    }

    return;
}

const sendWebSocketMessage = (message: any) => {
  if (socket.value && socket.value.readyState === WebSocket.OPEN) {
    socket.value.send(JSON.stringify(message))
  }
}

watch(title, async (newTitle) => {
    if (newTitle) {
        await fetchGameState();
        if (!error.value) {
            connectWebSocket()
        }
    }
}, { immediate: true })

onUnmounted(() => {
  if (socket.value) {
    socket.value.close()
  }
})
</script>

<style scoped>
.board {
    height: 100vh;
}
</style>
<template>
  <div class="h-screen overflow-hidden bg-gradient-to-b from-emerald-900 via-green-800 to-emerald-900 flex flex-col">
    <!-- Loading State -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="text-white text-xl">Loading game...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="flex-1 flex items-center justify-center">
      <div class="text-red-400 text-xl">{{ error }}</div>
    </div>

    <!-- Game Board -->
    <div v-else-if="gameState" class="flex-1 flex flex-col justify-between min-h-0">
      <!-- Side B (Top) -->
      <div class="flex-none">
        <!-- Side B Hero (flush to top) -->
        <div class="px-4 pt-2">
          <GameHero :hero="gameState.heroes.side_b" />
        </div>

        <!-- Side B Board (cards) -->
        <div class="px-4 pt-3 pb-2">
          <div class="flex justify-center">
            <div class="flex space-x-2 max-w-full overflow-x-auto">
              <BoardCard
                v-for="cardId in gameState.board.side_b.slice(0, maxCardsPerSide)"
                :key="cardId"
                :card="gameState.cards[cardId]"
                :name="getCardName(cardId)"
                :card-type="getCardType(cardId)"
              />
              <div v-if="gameState.board.side_b.length === 0" class="text-gray-400 text-sm py-4">
                No cards on board
              </div>
            </div>
          </div>
        </div>

        <!-- Side B Deck Indicator (upper-right) -->
        <div class="absolute top-4 right-4">
          <DeckIndicator :card-count="gameState.hands.side_b.length" />
        </div>
      </div>

      <!-- Center Battle Area -->
      <div class="flex-1 flex items-center justify-center min-h-0">
        <div class="text-center text-white/60">
          <div class="text-lg font-bold">Turn {{ gameState.turn }}</div>
          <div class="text-sm">{{ gameState.phase }} phase</div>
          <div class="text-sm">{{ gameState.active === 'side_a' ? 'Your' : 'Opponent' }} turn</div>
        </div>
      </div>

      <!-- Side A (Bottom) -->
      <div class="flex-none">
        <!-- Side A Deck Indicator (lower-right) -->
        <div class="absolute bottom-4 right-4">
          <DeckIndicator :card-count="gameState.hands.side_a.length" />
        </div>

        <!-- Side A Board (cards) -->
        <div class="px-4 pt-2 pb-3">
          <div class="flex justify-center">
            <div class="flex space-x-2 max-w-full overflow-x-auto">
              <BoardCard
                v-for="cardId in gameState.board.side_a.slice(0, maxCardsPerSide)"
                :key="cardId"
                :card="gameState.cards[cardId]"
                :name="getCardName(cardId)"
                :card-type="getCardType(cardId)"
              />
              <div v-if="gameState.board.side_a.length === 0" class="text-gray-400 text-sm py-4">
                No cards on board
              </div>
            </div>
          </div>
        </div>

        <!-- Side A Hero (flush to bottom) -->
        <div class="px-4 pb-2">
          <GameHero :hero="gameState.heroes.side_a" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from '../config/api.js'
import type { GameState } from '../types/game'
import GameHero from '../components/game/GameHero.vue'
import BoardCard from '../components/game/BoardCard.vue'
import DeckIndicator from '../components/game/DeckIndicator.vue'

const route = useRoute()
const gameState = ref<GameState | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const maxCardsPerSide = ref(6)

// Card name mapping - in a real app this would come from a card template API
const cardNameMap = ref<Record<string, string>>({})

const fetchGameState = async () => {
  try {
    const gameId = route.params.game_id
    const response = await axios.get(`/gameplay/games/${gameId}/`)

    const data = response.data
    gameState.value = data

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

const getCardName = (cardId: number): string => {
  const card = gameState.value?.cards[cardId]
  if (!card) return 'Unknown Card'
  return cardNameMap.value[card.template_slug] || card.template_slug
}

const getCardType = (cardId: number): 'minion' | 'spell' => {
  const card = gameState.value?.cards[cardId]
  // For now, assume all cards with attack/health are minions
  return (card?.attack !== undefined && card?.health !== undefined) ? 'minion' : 'spell'
}

onMounted(() => {
  fetchGameState()
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
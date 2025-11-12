<template>
  <div class="game-create-page">
    <div v-if="loading" class="flex items-center justify-center min-h-screen">
      <div class="text-center">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
        <p class="text-gray-600">Loading...</p>
      </div>
    </div>

    <div v-else-if="error" class="flex items-center justify-center min-h-screen">
      <div class="text-center">
        <p class="text-red-600 mb-4">{{ error }}</p>
        <router-link
          :to="{ name: 'Title', params: { slug: titleSlug } }"
          class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Back to Title
        </router-link>
      </div>
    </div>

    <div v-else>

      <section class="text-center bg-gray-300 h-24 flex items-center justify-center">
        <h1 class="font-display text-4xl font-bold text-gray-900 dark:text-gray-900">CREATE GAME</h1>
      </section>

      <main class="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 my-8">
        <!-- Game Mode Toggle -->
        <div class="mb-8">
          <div class="flex justify-center">
            <div class="inline-flex rounded-lg border border-gray-200 bg-white p-1 dark:border-gray-700 dark:bg-gray-800">
              <button
                @click="gameMode = 'pve'"
                :class="[
                  'rounded-md px-6 py-2 text-sm font-medium transition-colors',
                  gameMode === 'pve'
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                ]"
              >
                🤖 vs AI
              </button>
              <button
                @click="gameMode = 'pvp'"
                :class="[
                  'rounded-md px-6 py-2 text-sm font-medium transition-colors',
                  gameMode === 'pvp'
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                ]"
              >
                ⚔️ vs Player
              </button>
            </div>
          </div>
        </div>

        <div class="grid gap-8 md:grid-cols-2">
          <!-- Player Deck Selection -->
          <Panel title="Choose Your Deck">
            <div v-if="playerDecksLoading" class="text-center py-8">
              <p class="text-gray-600">Loading your decks...</p>
            </div>

            <div v-else-if="playerDecks.length === 0" class="text-center py-8">
              <p class="text-gray-600 mb-4">You don't have any decks for this title yet.</p>
              <router-link
                :to="{ name: 'DeckCreate', params: { slug: titleSlug } }"
                class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                Create a Deck First
              </router-link>
            </div>

            <div v-else class="space-y-3">
              <div
                v-for="deck in playerDecks"
                :key="deck.id"
                @click="selectedPlayerDeck = deck"
                :class="[
                  'cursor-pointer rounded-lg border-2 p-4 transition-colors',
                  selectedPlayerDeck?.id === deck.id
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                    : 'border-gray-200 hover:border-primary-300 dark:border-gray-700'
                ]"
              >
                <div class="flex items-center space-x-3">
                  <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100 text-sm font-bold text-primary-600">
                    {{ deck.hero.name.charAt(0) }}
                  </div>
                  <div class="flex-1">
                    <div class="font-medium text-gray-900 dark:text-white">{{ deck.name }}</div>
                    <div class="text-sm text-gray-600">
                      {{ deck.hero.name }} • {{ deck.card_count }} cards
                    </div>
                  </div>
                  <div v-if="selectedPlayerDeck?.id === deck.id" class="text-primary-600">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          </Panel>

          <!-- Opponent Deck Selection -->
          <Panel :title="gameMode === 'pve' ? 'Choose AI Opponent' : 'Choose Player Opponent'">
            <!-- PvE Mode: AI Decks -->
            <div v-if="gameMode === 'pve'">
              <div v-if="pveDecksLoading" class="text-center py-8">
                <p class="text-gray-600">Loading AI opponents...</p>
              </div>

              <div v-else-if="pveDecks.length === 0" class="text-center py-8">
                <p class="text-gray-600">No AI opponents available for this title yet.</p>
              </div>

              <div v-else class="space-y-3">
                <div
                  v-for="deck in pveDecks"
                  :key="deck.id"
                  @click="selectedOpponentDeck = deck"
                  :class="[
                    'cursor-pointer rounded-lg border-2 p-4 transition-colors',
                    selectedOpponentDeck?.id === deck.id
                      ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                      : 'border-gray-200 hover:border-green-300 dark:border-gray-700'
                  ]"
                >
                  <div class="flex items-center space-x-3">
                    <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 text-sm font-bold text-green-600">
                      🤖
                    </div>
                    <div class="flex-1">
                      <div class="font-medium text-gray-900 dark:text-white">{{ deck.name }}</div>
                      <div class="text-sm text-gray-600">
                        {{ deck.hero.name }} • {{ deck.card_count }} cards
                      </div>
                    </div>
                    <div v-if="selectedOpponentDeck?.id === deck.id" class="text-green-600">
                      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                      </svg>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- PvP Mode: Player Decks -->
            <div v-else>
              <div v-if="opponentDecksLoading" class="text-center py-8">
                <p class="text-gray-600">Loading opponent decks...</p>
              </div>

              <div v-else-if="opponentDecks.length === 0" class="text-center py-8">
                <p class="text-gray-600">No other players have decks for this title yet.</p>
              </div>

              <div v-else class="space-y-3">
                <div
                  v-for="deck in opponentDecks"
                  :key="deck.id"
                  @click="selectedOpponentDeck = deck"
                  :class="[
                    'cursor-pointer rounded-lg border-2 p-4 transition-colors',
                    selectedOpponentDeck?.id === deck.id
                      ? 'border-secondary-500 bg-secondary-50 dark:bg-secondary-900/20'
                      : 'border-gray-200 hover:border-secondary-300 dark:border-gray-700'
                  ]"
                >
                  <div class="flex items-center space-x-3">
                    <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary-100 text-sm font-bold text-secondary-600">
                      {{ deck.hero.name.charAt(0) }}
                    </div>
                    <div class="flex-1">
                      <div class="font-medium text-gray-900 dark:text-white">{{ deck.name }}</div>
                      <div class="text-sm text-gray-600">
                        {{ deck.hero.name }} • {{ deck.owner?.email }} • {{ deck.card_count }} cards
                      </div>
                    </div>
                    <div v-if="selectedOpponentDeck?.id === deck.id" class="text-secondary-600">
                      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                      </svg>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Panel>
        </div>

        <!-- Action Buttons -->
        <div class="mt-8 flex justify-center space-x-4">
          <router-link
            :to="{ name: 'Title', params: { slug: titleSlug } }"
            class="inline-flex items-center rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            Cancel
          </router-link>

          <button
            @click="createGame"
            :disabled="!canCreateGame || creating"
            :class="[
              'inline-flex items-center rounded-lg px-6 py-3 text-sm font-medium transition-colors',
              canCreateGame && !creating
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            ]"
          >
            {{ creating ? 'Creating Game...' : `Create ${gameMode === 'pve' ? 'PvE' : 'PvP'} Game` }}
          </button>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTitleStore } from '../stores/title'
import { useNotificationStore } from '../stores/notifications'
import axios from '../config/api'
import Panel from '../components/layout/Panel.vue'

interface DeckData {
  id: number
  name: string
  description: string
  hero: {
    id: number
    name: string
    slug: string
  }
  owner?: {
    email: string
  }
  card_count: number
  created_at: string
  updated_at: string
}

interface TitleData {
  id: number
  slug: string
  name: string
  description?: string
}

const route = useRoute()
const router = useRouter()
const titleStore = useTitleStore()
const notificationStore = useNotificationStore()

// Component state
const loading = ref<boolean>(true)
const error = ref<string | null>(null)
const creating = ref<boolean>(false)
const gameMode = ref<'pve' | 'pvp'>('pve')

// Data
const playerDecks = ref<DeckData[]>([])
const pveDecks = ref<DeckData[]>([])
const opponentDecks = ref<DeckData[]>([])
const playerDecksLoading = ref<boolean>(false)
const pveDecksLoading = ref<boolean>(false)
const opponentDecksLoading = ref<boolean>(false)

// Selections
const selectedPlayerDeck = ref<DeckData | null>(null)
const selectedOpponentDeck = ref<DeckData | null>(null)

// Computed
const title = computed((): TitleData | null => titleStore.currentTitle)
const titleSlug = computed(() => route.params.slug as string)

const canCreateGame = computed(() => {
  return selectedPlayerDeck.value && selectedOpponentDeck.value && !creating.value
})

// Methods
const fetchPlayerDecks = async (): Promise<void> => {
  try {
    playerDecksLoading.value = true
    const response = await axios.get(`/collection/titles/${titleSlug.value}/decks/`)
    playerDecks.value = response.data.decks || []
  } catch (err) {
    console.error('Error fetching player decks:', err)
    error.value = 'Failed to load your decks'
  } finally {
    playerDecksLoading.value = false
  }
}

const fetchPveDecks = async (): Promise<void> => {
  try {
    pveDecksLoading.value = true
    const response = await axios.get(`/titles/${titleSlug.value}/pve/`)
    pveDecks.value = response.data || []
  } catch (err) {
    console.error('Error fetching PvE decks:', err)
    error.value = 'Failed to load AI opponents'
  } finally {
    pveDecksLoading.value = false
  }
}

const fetchOpponentDecks = async (): Promise<void> => {
  try {
    opponentDecksLoading.value = true
    const response = await axios.get(`/collection/titles/${titleSlug.value}/opponents/`)
    opponentDecks.value = response.data.decks || []
  } catch (err) {
    console.error('Error fetching opponent decks:', err)
    error.value = 'Failed to load opponent decks'
  } finally {
    opponentDecksLoading.value = false
  }
}

const createGame = async (): Promise<void> => {
  if (!canCreateGame.value) return

  try {
    creating.value = true

    // Build game data based on mode
    const gameData: any = {
      player_deck_id: selectedPlayerDeck.value!.id
    }

    if (gameMode.value === 'pve') {
      gameData.ai_deck_id = selectedOpponentDeck.value!.id
    } else {
      gameData.opponent_deck_id = selectedOpponentDeck.value!.id
    }

    const response = await axios.post('/gameplay/games/new/', gameData)
    const gameId = response.data.id

    notificationStore.success(`${gameMode.value === 'pve' ? 'PvE' : 'PvP'} game created successfully!`)

    // Redirect to the game board
    router.push({
      name: 'Board',
      params: {
        game_id: gameId,
        slug: titleSlug.value
      }
    })
  } catch (err) {
    console.error('Error creating game:', err)
    notificationStore.handleApiError(err as Error)
  } finally {
    creating.value = false
  }
}

// Watchers
watch(gameMode, (newMode) => {
  // Clear selection when switching modes
  selectedOpponentDeck.value = null

  // Load opponent decks if switching to PvP and not already loaded
  if (newMode === 'pvp' && opponentDecks.value.length === 0) {
    fetchOpponentDecks()
  }
})

// Lifecycle
onMounted(async () => {
  try {
    loading.value = true

    // Fetch player decks and PvE decks (opponent decks loaded on demand)
    await Promise.all([
      fetchPlayerDecks(),
      fetchPveDecks()
    ])
  } catch (err) {
    console.error('Error initializing game create:', err)
    error.value = 'Failed to initialize page'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.game-create-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
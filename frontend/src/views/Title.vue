<template>
  <div class="title-page">

    <div v-if="!loading && !error && title">
      <section class="bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 py-16 text-center">
        <h1 class="font-display text-4xl font-bold">{{ title.name }}</h1>
      </section>

      <main class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-8 mt-8">

        <Panel v-if="title.description" title="Description">{{ title.description }}</Panel>

        <div class="flex justify-center">
          <router-link
            :to="{ name: 'TitleCards', params: { slug: title.slug } }"
            class="inline-flex items-center rounded-lg bg-primary-600 px-6 py-3 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
          >
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
            </svg>
            View Full Collection
          </router-link>
        </div>

        <div class="grid gap-8 sm:grid-cols-2">
          <Panel title="Decks">
            <div v-if="decks.length > 0" class="space-y-3">
              <div
                v-for="deck in decks"
                :key="deck.id"
                class="flex items-center justify-between rounded-lg bg-gray-50 p-3 hover:bg-gray-100 transition-colors dark:bg-gray-800 dark:hover:bg-gray-700"
              >
                <div class="flex items-center space-x-3">
                  <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100 text-sm font-bold text-primary-600">
                    {{ deck.hero.name.charAt(0) }}
                  </div>
                  <div>
                    <router-link
                      :to="{ name: 'DeckDetail', params: { id: deck.id } }"
                      class="font-medium text-gray-900 hover:text-primary-600 dark:text-white"
                    >
                      {{ deck.name }}
                    </router-link>
                    <div class="text-sm text-gray-600">
                      {{ deck.hero.name }} • {{ deck.card_count }} cards
                    </div>
                  </div>
                </div>
                <div class="text-sm text-gray-500">
                  {{ formatDate(deck.updated_at) }}
                </div>
              </div>

              <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
                <router-link
                  :to="{ name: 'DeckCreate', params: { slug: title.slug } }"
                  class="flex items-center justify-center w-full rounded-lg border-2 border-dashed border-gray-300 p-3 text-sm font-medium text-gray-600 hover:border-primary-400 hover:text-primary-600 transition-colors"
                >
                  <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                  </svg>
                  Create New Deck
                </router-link>
              </div>
            </div>

            <div v-else class="text-center py-8">
              <p class="text-gray-600 mb-4">You don't have any decks for this title yet.</p>
              <router-link
                :to="{ name: 'DeckCreate', params: { slug: title.slug } }"
                class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                </svg>
                Create Your First Deck
              </router-link>
            </div>

            <div v-if="decksLoading" class="text-center py-4">
              <p class="text-gray-600">Loading decks...</p>
            </div>
          </Panel>

          <Panel title="Games">
            <div v-if="games.length > 0" class="space-y-3">
              <div
                v-for="game in games"
                :key="game.id"
                class="flex items-center justify-between rounded-lg bg-gray-50 p-3 hover:bg-gray-100 transition-colors dark:bg-gray-800 dark:hover:bg-gray-700"
              >
                <div class="flex items-center space-x-3">
                  <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 text-sm font-bold text-green-600">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h.01M19 4v3a3 3 0 01-3 3h-1m-1 0h-1m1 0V6a1 1 0 00-1-1h-2a1 1 0 00-1 1v3"></path>
                    </svg>
                  </div>
                  <div>
                    <router-link
                      :to="{ name: 'GameBoard', params: { game_id: game.id } }"
                      class="font-medium text-gray-900 hover:text-green-600 dark:text-white"
                    >
                      {{ game.name }}
                    </router-link>
                    <div class="text-sm text-gray-600">
                      Game ID: {{ game.id }}
                    </div>
                  </div>
                </div>
                <div class="flex items-center">
                  <router-link
                    :to="{ name: 'Board', params: { game_id: game.id, slug: title.slug } }"
                    class="inline-flex items-center rounded-lg bg-green-600 px-3 py-1 text-sm font-medium text-white hover:bg-green-700 transition-colors"
                  >
                    Join Game
                  </router-link>
                </div>
              </div>
            </div>

            <div v-else-if="!gamesLoading" class="text-center py-8">
              <p class="text-gray-600 mb-4">No active games at the moment.</p>
              <router-link
                :to="{ name: 'GameCreate', params: { slug: title.slug } }"
                class="inline-flex items-center rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 transition-colors"
              >
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h.01M19 4v3a3 3 0 01-3 3h-1m-1 0h-1m1 0V6a1 1 0 00-1-1h-2a1 1 0 00-1 1v3"></path>
                </svg>
                Create Game
              </router-link>
            </div>

            <div v-if="gamesLoading" class="text-center py-4">
              <p class="text-gray-600">Loading games...</p>
            </div>
          </Panel>
        </div>

        <!-- ELO Ratings & Leaderboard -->
        <Panel title="⚔️ PvP Rankings" v-if="isAuthenticated">
          <div v-if="!leaderboardLoading" class="space-y-4">
            <!-- User's Rating -->
            <div v-if="userRating" class="rounded-lg bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 p-4 border border-amber-200 dark:border-amber-800">
              <div class="flex items-center justify-between">
                <div>
                  <div class="text-sm font-medium text-gray-600 dark:text-gray-400">Your Rating</div>
                  <div class="text-3xl font-bold text-amber-600 dark:text-amber-400">
                    {{ userRating.elo_rating }}
                  </div>
                </div>
                <div class="text-right">
                  <div class="text-sm text-gray-600 dark:text-gray-400">Record</div>
                  <div class="text-lg font-semibold text-gray-900 dark:text-white">
                    {{ userRating.wins }}W - {{ userRating.losses }}L
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="rounded-lg bg-gray-50 dark:bg-gray-800 p-4 text-center">
              <p class="text-sm text-gray-600 dark:text-gray-400">
                No rating yet. Play your first PvP match to get ranked!
              </p>
            </div>

            <!-- Top 3 Players -->
            <div class="space-y-2">
              <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Top Players</h3>
              <div
                v-for="(player, index) in topPlayers"
                :key="player.id"
                class="flex items-center justify-between p-3 rounded-lg transition-colors"
                :class="{
                  'bg-amber-50 dark:bg-amber-900/20': index === 0,
                  'bg-gray-50 dark:bg-gray-800': index === 1,
                  'bg-orange-50 dark:bg-orange-900/20': index === 2
                }"
              >
                <div class="flex items-center gap-3">
                  <span class="text-2xl">
                    {{ index === 0 ? '🥇' : index === 1 ? '🥈' : '🥉' }}
                  </span>
                  <div>
                    <div class="font-medium text-gray-900 dark:text-white">
                      {{ player.display_name }}
                      <span v-if="player.id === authStore.user?.id" class="ml-1 text-xs text-blue-600 dark:text-blue-400">(You)</span>
                    </div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">
                      {{ player.wins }}W - {{ player.losses }}L
                    </div>
                  </div>
                </div>
                <div class="text-lg font-bold text-amber-600 dark:text-amber-400">
                  {{ player.elo_rating }}
                </div>
              </div>
            </div>

            <!-- View Full Leaderboard Link -->
            <div class="pt-3 border-t border-gray-200 dark:border-gray-700">
              <router-link
                :to="{ name: 'Leaderboard', params: { slug: title.slug } }"
                class="flex items-center justify-center w-full rounded-lg bg-amber-100 dark:bg-amber-900/30 p-3 text-sm font-medium text-amber-900 dark:text-amber-200 hover:bg-amber-200 dark:hover:bg-amber-900/50 transition-colors"
              >
                🏆 View Full Leaderboard
                <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                </svg>
              </router-link>
            </div>
          </div>

          <div v-else class="text-center py-4">
            <p class="text-gray-600 dark:text-gray-400">Loading rankings...</p>
          </div>
        </Panel>
      </main>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useTitleStore } from '../stores/title'
import { useAuthStore } from '../stores/auth'
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
  card_count: number
  created_at: string
  updated_at: string
}

interface GameData {
  id: number
  name: string
}

interface LeaderboardPlayer {
  id: number
  username?: string
  display_name: string
  avatar?: string
  elo_rating: number
  wins: number
  losses: number
  total_games: number
}

const route = useRoute()
const titleStore = useTitleStore()
const authStore = useAuthStore()

// Use the title from the store instead of local state
const title = computed(() => titleStore.currentTitle)
const loading = computed(() => titleStore.loading)
const error = computed(() => titleStore.error)
const isAuthenticated = computed(() => authStore.isAuthenticated)

const decks = ref<DeckData[]>([])
const games = ref<GameData[]>([])
const topPlayers = ref<LeaderboardPlayer[]>([])
const userRating = ref<LeaderboardPlayer | null>(null)
const decksLoading = ref<boolean>(false)
const gamesLoading = ref<boolean>(false)
const leaderboardLoading = ref<boolean>(false)

// Title data now comes from the store via router preloading

const fetchDecks = async (): Promise<void> => {
  if (!title.value) return

  try {
    decksLoading.value = true
    const slug = route.params.slug as string
    const response = await axios.get(`/collection/titles/${slug}/decks/`)
    decks.value = response.data.decks || []
  } catch (err) {
    console.error('Error fetching decks:', err)
    // Don't show error for decks if title loaded successfully
    // Just log it and show empty state
  } finally {
    decksLoading.value = false
  }
}

const fetchGames = async (): Promise<void> => {
  try {
    gamesLoading.value = true
    const slug = route.params.slug as string
    const response = await axios.get(`/titles/${slug}/games/`)
    games.value = response.data.games || []
  } catch (err) {
    console.error('Error fetching games:', err)
    // Don't show error for games if title loaded successfully
    // Just log it and show empty state
  } finally {
    gamesLoading.value = false
  }
}

const fetchLeaderboard = async (): Promise<void> => {
  if (!title.value || !isAuthenticated.value) return

  try {
    leaderboardLoading.value = true
    const slug = route.params.slug as string

    // Fetch top players and user's rating in parallel
    const [leaderboardResponse, userRatingResponse] = await Promise.all([
      axios.get(`/gameplay/${slug}/leaderboard/`, {
        params: { limit: 3 } // Only need top 3 for display
      }),
      axios.get(`/gameplay/${slug}/my-rating/`)
    ])

    topPlayers.value = leaderboardResponse.data as LeaderboardPlayer[]
    userRating.value = userRatingResponse.data as LeaderboardPlayer
  } catch (err) {
    console.error('Error fetching leaderboard:', err)
    // Don't show error, just log it
  } finally {
    leaderboardLoading.value = false
  }
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

// Watch for title to be loaded and then fetch related data
watch(title, async (newTitle) => {
  if (newTitle) {
    await fetchDecks()
    await fetchGames()
    await fetchLeaderboard()
  }
}, { immediate: true })

onMounted(() => {
  // Title will be loaded by router, so we just need to watch for it
})
</script>

<style scoped>
.title-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
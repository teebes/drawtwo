<template>
  <div class="games-page">
    <!-- Header -->
    <section class="banner">
      <h1>Games</h1>
    </section>

    <main class="mx-auto max-w-4xl w-full px-4 sm:px-6 lg:px-8 space-y-8 mt-8">
      <!-- Loading State -->
      <div v-if="loading" class="text-center p-8">
        <p class="text-gray-600 dark:text-gray-400">Loading games...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="text-center p-8">
        <Panel variant="error">
          <p class="text-red-600 dark:text-red-400">{{ error }}</p>
        </Panel>
      </div>

      <!-- Content -->
      <template v-else>
        <!-- Stats Panel -->
         <section class="flex flex-row sm:flex-row gap-8 justify-center">
            <Panel class="flex-1">
                    <div class="ranked-play text-center flex-1">
                        <div class="text-lg text-primary-600 dark:text-primary-500">Ranked Play</div>
                        <div>{{ stats.ranked.wins }}W - {{ stats.ranked.losses }}L</div>
                        <div>
                            <span class="text-sm text-gray-500 dark:text-gray-400">[ {{ currentRating }} ]</span>
                        </div>

                    </div>
            </Panel>

            <Panel class="flex-1">
                <div class="friendly-play text-center flex-1">
                    <div class="text-lg text-secondary-600 dark:text-secondary-500">Friendly Play</div>
                    {{ stats.friendly.total }} Games Played
                </div>
            </Panel>
        </section>

        <!-- New Game-->
         <section>
          <router-link
            :to="{ name: 'GameCreate', params: { slug: titleSlug } }"
            class="flex mt-4 items-center justify-center w-full rounded-lg border-2 border-dashed border-primary-500 p-3 text-sm font-medium text-primary-500 hover:border-primary-600 hover:text-primary-600 transition-colors">
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
            </svg>
            New Game
          </router-link>
      </section>

        <!-- Games List -->
        <section v-if="games.length > 0">
          <div class="space-y-2">
            <div
              v-for="game in games"
              :key="game.id"
              class="flex items-center rounded-lg bg-gray-50 dark:bg-gray-800 p-3 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
              @click="viewGame(game)"
            >
              <!-- Game Type Badge -->
              <div
                :class="[
                  'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-semibold',
                  game.type === 'ranked'
                    ? 'bg-primary-500 text-white'
                    : game.type === 'friendly'
                    ? 'bg-secondary-500 text-gray-800'
                    : 'bg-gray-500 text-white'
                ]"
                :title="game.type === 'ranked' ? 'Ranked Game' : game.type === 'friendly' ? 'Friendly Game' : 'PvE Game'"
              >
                {{ game.type === 'ranked' ? 'R' : game.type === 'friendly' ? 'F' : 'AI' }}
              </div>

              <!-- Outcome Indicator (only for ended games) -->
              <div
                v-if="game.status === 'ended' && game.outcome"
                :class="[
                  'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ml-2',
                  game.outcome === 'win'
                    ? 'bg-green-500 text-white'
                    : game.outcome === 'loss'
                    ? 'bg-red-500 text-white'
                    : 'bg-gray-500 text-white'
                ]"
                :title="game.outcome === 'win' ? 'Victory' : game.outcome === 'loss' ? 'Defeat' : 'Draw'"
              >
                {{ game.outcome === 'win' ? 'W' : game.outcome === 'loss' ? 'L' : 'D' }}
              </div>

              <!-- Turn Indicator (only for in-progress games) -->
              <div
                v-if="game.status === 'in_progress'"
                :class="[
                  'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ml-2',
                  game.is_user_turn
                    ? 'bg-blue-500 text-white animate-pulse'
                    : 'bg-gray-400 text-white'
                ]"
                :title="game.is_user_turn ? 'Your turn' : 'Waiting for opponent'"
              >
                {{ game.is_user_turn ? '→' : '...' }}
              </div>

              <!-- Opponent Info -->
              <div class="flex-1 ml-4">
                <div class="font-medium text-gray-900 dark:text-gray-100 truncate">
                  vs {{ game.opponent_name }}
                  <span
                    v-if="game.status === 'in_progress'"
                    :class="[
                      'ml-2 text-xs',
                      game.is_user_turn
                        ? 'text-blue-600 dark:text-blue-400 font-semibold'
                        : 'text-gray-500 dark:text-gray-400'
                    ]"
                  >
                    ({{ game.is_user_turn ? 'Your turn' : 'Opponent\'s turn' }})
                  </span>
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400">
                  {{ game.user_hero }} vs {{ game.opponent_hero }}
                </div>
              </div>

              <!-- ELO Change (if applicable) -->
              <div
                v-if="game.elo_change !== null"
                :class="[
                  'flex-shrink-0 text-sm font-bold ml-4',
                  game.elo_change > 0
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-red-600 dark:text-red-400'
                ]"
              >
                {{ game.elo_change > 0 ? '+' : '' }}{{ game.elo_change }}
              </div>

              <!-- Date -->
              <div class="flex-shrink-0 text-xs text-gray-500 dark:text-gray-400 ml-4">
                {{ formatDate(game.created_at) }}
              </div>
            </div>
          </div>
        </section>

        <!-- Empty State -->
        <Panel v-else>
          <div class="text-center py-8">
            <p class="text-gray-600 dark:text-gray-400">No games yet.</p>
            <p class="text-sm text-gray-500 dark:text-gray-500 mt-2">
              Play some games to see your history here!
            </p>
          </div>
        </Panel>

        <!-- Pagination -->
        <div v-if="pagination.total_pages > 1" class="flex justify-center items-center space-x-4">
          <GameButton
            variant="secondary"
            size="sm"
            :disabled="!pagination.has_previous"
            @click="goToPage(pagination.page - 1)"
          >
            ← Previous
          </GameButton>

          <span class="text-sm text-gray-600 dark:text-gray-400">
            Page {{ pagination.page }} of {{ pagination.total_pages }}
          </span>

          <GameButton
            variant="secondary"
            size="sm"
            :disabled="!pagination.has_next"
            @click="goToPage(pagination.page + 1)"
          >
            Next →
          </GameButton>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../config/api'
import Panel from '../components/layout/Panel.vue'
import GameButton from '../components/ui/GameButton.vue'
import { useNotificationStore } from '../stores/notifications'

interface GameStats {
  total: number
  wins: number
  losses: number
}

interface FriendlyStats {
  total: number
}

interface Stats {
  ranked: GameStats
  friendly: FriendlyStats
  current_rating?: number
}

interface GameHistoryItem {
  id: number
  type: 'ranked' | 'friendly' | 'pve'
  status: 'init' | 'in_progress' | 'ended'
  opponent_name: string
  opponent_hero: string | null
  user_hero: string | null
  outcome: 'win' | 'loss' | 'draw' | null
  is_user_turn: boolean | null
  elo_change: number | null
  created_at: string
}

interface Pagination {
  page: number
  total_pages: number
  total_games: number
  has_next: boolean
  has_previous: boolean
}

const route = useRoute()
const router = useRouter()
const notificationStore = useNotificationStore()

const loading = ref(true)
const error = ref<string | null>(null)
const stats = ref<Stats>({
  ranked: { total: 0, wins: 0, losses: 0 },
  friendly: { total: 0 },
  current_rating: 1200
})
const games = ref<GameHistoryItem[]>([])
const currentRating = ref<number>(1200)
const pagination = ref<Pagination>({
  page: 1,
  total_pages: 1,
  total_games: 0,
  has_next: false,
  has_previous: false
})

const titleSlug = ref(route.params.slug as string)

const fetchGamesHistory = async (page: number = 1) => {
  try {
    loading.value = true
    error.value = null

    const response = await axios.get(`/titles/${titleSlug.value}/games/history/`, {
      params: { page }
    })

    stats.value = response.data.stats
    games.value = response.data.games
    pagination.value = response.data.pagination
    currentRating.value = response.data.stats.current_rating || 1200
  } catch (err: any) {
    console.error('Error fetching games history:', err)
    error.value = err.response?.data?.error || err.message || 'Failed to load games history'
    notificationStore.handleApiError(err)
  } finally {
    loading.value = false
  }
}

const goToPage = (page: number) => {
  if (page >= 1 && page <= pagination.value.total_pages) {
    fetchGamesHistory(page)
  }
}

const viewGame = (game: GameHistoryItem) => {
  router.push({
    name: 'Board',
    params: {
      slug: titleSlug.value,
      game_id: game.id
    }
  })
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) {
    return 'Just now'
  } else if (diffMins < 60) {
    return `${diffMins}m ago`
  } else if (diffHours < 24) {
    return `${diffHours}h ago`
  } else if (diffDays < 7) {
    return `${diffDays}d ago`
  } else {
    return date.toLocaleDateString()
  }
}

// Watch for route changes (if navigating between titles)
watch(
  () => route.params.slug,
  (newSlug) => {
    if (newSlug && newSlug !== titleSlug.value) {
      titleSlug.value = newSlug as string
      fetchGamesHistory(1)
    }
  }
)

onMounted(() => {
  fetchGamesHistory()
})
</script>

<style scoped>
.games-page {
  display: flex;
  flex-direction: column;
}
</style>

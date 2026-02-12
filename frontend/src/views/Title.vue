<template>
  <div class="title-page flex flex-col">
    <!-- Access Denied Message -->
    <div v-if="accessDenied" class="max-w-2xl mx-auto px-4 py-16 text-center">
      <div class="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-8">
        <svg class="w-16 h-16 mx-auto text-red-600 dark:text-red-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
        </svg>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Access Denied</h2>
        <p class="text-gray-700 dark:text-gray-300 mb-6">
          You do not have permission to view this title. This title may be unpublished or in draft status.
        </p>
        <router-link
          to="/"
          class="inline-flex items-center rounded-lg bg-primary-600 px-6 py-3 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
        >
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
          </svg>
          Back to Home
        </router-link>
      </div>
    </div>

    <div v-else-if="!loading && !error && title">
      <section class="banner" v-if="false">
        <h1 class="">{{ title?.name }}</h1>
      </section>

      <img v-if="title.art_url" :src="title.art_url" :alt="title.name" class="banner h-48 w-auto mx-auto" />

      <main class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-8 mt-8">

        <Panel v-if="title.description" title="Description">{{ title.description }}</Panel>

        <!-- Collection / Games -->
        <div class="flex w-full">
          <router-link
            :to="{ name: 'Collection', params: { slug: title.slug } }"
            class="flex-1 flex items-center justify-center text-xl font-bold rounded-lg border border-transparent  hover:border-gray-300 dark:hover:border-gray-800 p-4 underline decoration-dotted underline-offset-8 decoration-gray-500"
          >Collection</router-link>
          <router-link
            :to="{ name: 'Games', params: { slug: title.slug } }"
            class="flex-1 flex items-center justify-center text-xl font-bold rounded-lg border border-transparent  hover:border-gray-300 dark:hover:border-gray-800 p-4 underline decoration-dotted underline-offset-8 decoration-gray-500"
          >Games</router-link>
        </div>

        <div class="flex flex-col md:flex-row space-y-8 md:space-y-0 md:space-x-24 md:py-16">

          <!-- Quick Actions -->
          <section class="quick-actions flex-[2]">
            <!-- New Game-->
            <router-link
              :to="{ name: 'GameCreate', params: { slug: title.slug } }"
              class="flex mt-4 items-center justify-center w-full rounded-lg border-2 border-dashed border-primary-500 p-3 text-sm font-medium text-primary-500 hover:border-primary-600 hover:text-primary-600 transition-colors mb-8">
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
              </svg>
              New Game
            </router-link>

            <!-- Notifications -->
            <TitleNotifications
              :notifications="notifications"
              :decks="decks"
              :decks-loading="decksLoading"
              :title-slug="(route.params.slug as string)"
              @challenge-accepted="handleChallengeAccepted"
              @challenge-declined="handleChallengeDeclined" />

          </section>

          <!-- Leaderboard-->
          <section class="leaderboard flex-1">
            <div class="mb-2 flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-2">
              <h2 class="text-2xl font-bold text-gray-800 dark:text-gray-200">Ladder</h2>
              <div class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide">
                <button
                  type="button"
                  class="rounded-full px-3 py-1 transition-colors"
                  :class="leaderboardLadder === 'rapid' ? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900' : 'bg-gray-200 text-gray-600 hover:bg-gray-300 dark:bg-gray-800 dark:text-gray-300'"
                  @click="leaderboardLadder = 'rapid'"
                >
                  Rapid
                </button>
                <button
                  type="button"
                  class="rounded-full px-3 py-1 transition-colors"
                  :class="leaderboardLadder === 'daily' ? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900' : 'bg-gray-200 text-gray-600 hover:bg-gray-300 dark:bg-gray-800 dark:text-gray-300'"
                  @click="leaderboardLadder = 'daily'"
                >
                  Daily
                </button>
              </div>
            </div>

            <div v-if="!leaderboardLoading" class="space-y-4 mt-4">

              <div v-for="(player, index) in topPlayers" :key="player.id" class="flex items-center">
                <div class="w-10">{{ index + 1}}</div>
                <div class="flex-grow text-lg font-bold">{{ player.display_name }}</div>
                <div class="text-gray-500">[ {{ player.elo_rating }} ]</div>
              </div>

              <router-link
                v-if="route.params.slug"
                :to="{ name: 'Leaderboard', params: { slug: route.params.slug } }"
                class="text-left block text-xs font-semibold uppercase tracking-wide text-gray-500 hover:text-primary-500 dark:text-gray-400"
              >
                Full Ladder
              </router-link>
            </div>



            <div v-else class="text-center py-4">
              <p class="text-gray-600 dark:text-gray-400">Loading leaderboard...</p>
            </div>
          </section>

        </div>

        <Howto />

      </main>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useTitleStore } from '../stores/title'
import { useAuthStore } from '../stores/auth'
import axios from '../config/api'
import Panel from '../components/layout/Panel.vue'
import TitleNotifications from '../components/title/TitleNotifications.vue'
import type { Notification } from '../types/notification'
import type { LadderType } from '../types/game'
import Howto from './Howto.vue'

interface DeckApiData {
  id: number
  name: string
  description: string
  hero: {
    id: number
    name: string
    slug: string
    art_url?: string | null
  }
  card_count: number
  created_at: string
  updated_at: string
}

interface DeckData extends DeckApiData {
  formattedUpdatedAt: string
}

interface GameData {
  id: number
  name: string
  type: 'pve' | 'ranked' | 'friendly'
  is_user_turn: boolean
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

// Check if access is denied (403 error)
const accessDenied = computed(() => titleStore.errorStatus === 403)

const decks = ref<DeckData[]>([])
const games = ref<GameData[]>([])
const topPlayers = ref<LeaderboardPlayer[]>([])
const notifications = ref<Notification[]>([])
const decksLoading = ref<boolean>(false)
const gamesLoading = ref<boolean>(false)
const leaderboardLoading = ref<boolean>(false)
const notificationsLoading = ref<boolean>(false)
const leaderboardLadder = ref<LadderType>('daily')
const NOTIFICATION_REFRESH_INTERVAL_MS = 10000
let notificationsRefreshTimer: ReturnType<typeof setInterval> | null = null

// Title data now comes from the store via router preloading

const fetchDecks = async (): Promise<void> => {
  if (!title.value) return

  try {
    decksLoading.value = true
    const slug = route.params.slug as string
    const response = await axios.get(`/collection/titles/${slug}/decks/`)
    const deckList: DeckData[] = (response.data.decks || []).map((deck: DeckApiData) => ({
      ...deck,
      formattedUpdatedAt: formatDate(deck.updated_at)
    }))
    decks.value = deckList
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

    const response = await axios.get(`/gameplay/${slug}/leaderboard/`, {
      params: { limit: 3, ladder_type: leaderboardLadder.value } // Only need top 3 for display
    })

    topPlayers.value = response.data as LeaderboardPlayer[]
  } catch (err) {
    console.error('Error fetching leaderboard:', err)
    // Don't show error, just log it
  } finally {
    leaderboardLoading.value = false
  }
}

const fetchNotifications = async (): Promise<void> => {
  if (!title.value || !isAuthenticated.value) return
  if (notificationsLoading.value) return

  try {
    notificationsLoading.value = true
    const slug = route.params.slug as string
    const response = await axios.get(`/titles/${slug}/notifications/`)
    notifications.value = response.data as Notification[]
  } catch (err) {
    console.error('Error fetching notifications:', err)
  } finally {
    notificationsLoading.value = false
  }
}

const stopNotificationsRefresh = (): void => {
  if (notificationsRefreshTimer !== null) {
    clearInterval(notificationsRefreshTimer)
    notificationsRefreshTimer = null
  }
}

const startNotificationsRefresh = (): void => {
  stopNotificationsRefresh()

  if (!title.value || !isAuthenticated.value) return

  notificationsRefreshTimer = setInterval(() => {
    if (document.visibilityState !== 'visible') return
    void fetchNotifications()
  }, NOTIFICATION_REFRESH_INTERVAL_MS)
}

const handleVisibilityChange = (): void => {
  if (document.visibilityState !== 'visible') return
  if (!title.value || !isAuthenticated.value) return
  void fetchNotifications()
}

// Event handlers for TitleNotifications component
const handleChallengeAccepted = (challengeId: number) => {
  notifications.value = notifications.value.filter(n => !(n.type === 'game_challenge' && n.ref_id === challengeId))
}

const handleChallengeDeclined = (challengeId: number) => {
  notifications.value = notifications.value.filter(n => !(n.type === 'game_challenge' && n.ref_id === challengeId))
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
    await Promise.all([
      fetchDecks(),
      fetchGames(),
      fetchLeaderboard(),
      fetchNotifications()
    ])
  }
}, { immediate: true })

watch(leaderboardLadder, async () => {
  if (title.value) {
    await fetchLeaderboard()
  }
})

watch([title, isAuthenticated], ([newTitle, newIsAuthenticated]) => {
  if (newTitle && newIsAuthenticated) {
    startNotificationsRefresh()
    return
  }
  stopNotificationsRefresh()
}, { immediate: true })

onMounted(() => {
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  stopNotificationsRefresh()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
img.banner {
  filter: brightness(0.0);
}

.dark img.banner {
  filter: brightness(0.8);
}
</style>

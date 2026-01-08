<template>
  <div class="ranked-queue-page">
    <!-- Header -->
    <section class="text-center bg-gray-300 h-24 flex items-center justify-center">
      <h1 class="font-display text-4xl font-bold text-gray-900">{{ ladderTitle }} QUEUE</h1>
    </section>

    <main class="mx-auto max-w-2xl px-4 sm:px-6 lg:px-8 my-8">
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
        <p class="text-gray-600">Loading queue status...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="text-center py-12">
        <div class="rounded-lg border border-red-200 bg-red-50 p-6">
          <p class="text-red-600 mb-4">{{ error }}</p>
          <router-link
            :to="{ name: 'GameCreate', params: { slug: titleSlug } }"
            class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Back to Game Setup
          </router-link>
        </div>
      </div>

      <!-- Queue Active State -->
      <div v-else-if="!timedOut && inQueue" class="text-center py-12">
        <div class="mb-8">
          <!-- Animated searching icon -->
          <div class="relative inline-block">
            <div class="animate-pulse">
              <svg class="w-24 h-24 text-primary-600 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
              </svg>
            </div>
            <div class="absolute inset-0 animate-ping">
              <svg class="w-24 h-24 text-primary-400 mx-auto opacity-75" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke-width="2"></circle>
              </svg>
            </div>
          </div>
        </div>

        <h2 class="text-2xl font-bold text-gray-900 mb-4">Searching for Opponent...</h2>

        <div class="mb-6">
          <p class="text-gray-600 mb-2">
            Deck: <span class="font-semibold text-gray-900">{{ queueEntry?.deck.name }}</span>
          </p>
          <p class="text-gray-600 mb-2">
            Your Rating: <span class="font-semibold text-gray-900">{{ queueEntry?.elo_rating }}</span>
          </p>
        </div>

        <!-- Timer -->
        <div v-if="!isDaily" class="mb-8">
          <div class="text-5xl font-bold text-primary-600 mb-2">
            {{ formattedTime }}
          </div>
          <p class="text-sm text-gray-500">Time in queue</p>
          <div class="mt-4 max-w-xs mx-auto">
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div
                class="bg-primary-600 h-2 rounded-full transition-all duration-1000"
                :style="{ width: `${timeProgress}%` }"
              ></div>
            </div>
            <p class="text-xs text-gray-500 mt-2">Queue timeout in {{ timeRemaining }}s</p>
          </div>
        </div>
        <div v-else class="mb-8 text-sm text-gray-500">
          You can leave this page and stay in the daily queue until a match is found.
        </div>

        <!-- Cancel Button -->
        <button
          @click="leaveQueue"
          :disabled="leaving"
          class="inline-flex items-center rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ leaving ? 'Leaving...' : 'Leave Queue' }}
        </button>
      </div>

      <!-- Timeout State -->
      <div v-else-if="timedOut && !isDaily" class="text-center py-12">
        <div class="mb-8">
          <svg class="w-24 h-24 text-gray-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
        </div>

        <h2 class="text-2xl font-bold text-gray-900 mb-4">Queue Timeout</h2>
        <p class="text-gray-600 mb-8">
          No opponent found within 1 minute. Would you like to try again?
        </p>

        <div class="flex justify-center space-x-4">
          <button
            @click="requeue"
            :disabled="requeueing"
            class="inline-flex items-center rounded-lg bg-primary-600 px-6 py-3 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ requeueing ? 'Requeueing...' : 'Requeue' }}
          </button>
          <router-link
            :to="{ name: 'GameCreate', params: { slug: titleSlug } }"
            class="inline-flex items-center rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Back to Game Setup
          </router-link>
        </div>
      </div>

      <!-- Not in Queue State -->
      <div v-else class="text-center py-12">
        <p class="text-gray-600 mb-4">You are not currently in the {{ ladderLabel }} queue.</p>
        <router-link
          :to="{ name: 'GameCreate', params: { slug: titleSlug } }"
          class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Back to Game Setup
        </router-link>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNotificationStore } from '../stores/notifications'
import { useAuthStore } from '../stores/auth'
import axios from '../config/api'
import type { LadderType } from '../types/game'

interface QueueEntry {
  id: number
  status: string
  elo_rating: number
  queued_at: string
  ladder_type: LadderType
  deck: {
    id: number
    name: string
    hero: string
  }
  title: {
    id: number
    name: string
    slug: string
  }
}

const route = useRoute()
const router = useRouter()
const notificationStore = useNotificationStore()
const authStore = useAuthStore()

// Component state
const loading = ref<boolean>(true)
const error = ref<string | null>(null)
const inQueue = ref<boolean>(false)
const queueEntry = ref<QueueEntry | null>(null)
const leaving = ref<boolean>(false)
const requeueing = ref<boolean>(false)
const timedOut = ref<boolean>(false)

// Timer state
const elapsedSeconds = ref<number>(0)
const timerInterval = ref<number | null>(null)
const pollInterval = ref<number | null>(null)

// Constants
const QUEUE_TIMEOUT_SECONDS = 60
const POLL_INTERVAL_MS = 3000 // Poll every 3 seconds

// Computed
const titleSlug = computed(() => route.params.slug as string)
const deckId = computed(() => route.query.deck_id as string)
const ladderType = computed(() => (route.query.ladder_type as LadderType) || 'rapid')
const isDaily = computed(() => ladderType.value === 'daily')
const ladderLabel = computed(() => (isDaily.value ? 'daily' : 'rapid'))
const ladderTitle = computed(() => ladderLabel.value.toUpperCase())

const formattedTime = computed(() => {
  const minutes = Math.floor(elapsedSeconds.value / 60)
  const seconds = elapsedSeconds.value % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
})

const timeProgress = computed(() => {
  return (elapsedSeconds.value / QUEUE_TIMEOUT_SECONDS) * 100
})

const timeRemaining = computed(() => {
  return Math.max(0, QUEUE_TIMEOUT_SECONDS - elapsedSeconds.value)
})

// Methods
const fetchQueueStatus = async (): Promise<void> => {
  try {
    const response = await axios.get(`/gameplay/matchmaking/status/${titleSlug.value}/`, {
      params: { ladder_type: ladderType.value }
    })
    inQueue.value = response.data.in_queue
    queueEntry.value = response.data.queue_entry

    // If we find a matched game, redirect to it
    if (queueEntry.value && queueEntry.value.status === 'matched') {
      // Need to get the game ID from the queue entry
      // For now, let's fetch the user's current games to find the new ranked game
      const gamesResponse = await axios.get('/gameplay/games/')
      const rankedGames = gamesResponse.data.games.filter((g: any) => g.type === 'ranked')
      if (rankedGames.length > 0) {
        const latestGame = rankedGames[0]
        notificationStore.success('Match found! Starting game...')
        router.push({
          name: 'Board',
          params: {
            slug: titleSlug.value,
            game_id: latestGame.id
          }
        })
      }
    }

    // If not in queue anymore (cancelled or matched), stop polling
    if (!inQueue.value) {
      stopPolling()
      stopTimer()
    }
  } catch (err) {
    console.error('Error fetching queue status:', err)
    // Don't show error on polling failures, just log it
  }
}

const leaveQueue = async (): Promise<void> => {
  try {
    leaving.value = true
    await axios.post(`/gameplay/matchmaking/leave/${titleSlug.value}/`, null, {
      params: { ladder_type: ladderType.value }
    })
    notificationStore.success('Left matchmaking queue')
    stopPolling()
    stopTimer()
    router.push({
      name: 'GameCreate',
      params: { slug: titleSlug.value }
    })
  } catch (err) {
    console.error('Error leaving queue:', err)
    notificationStore.handleApiError(err as Error)
  } finally {
    leaving.value = false
  }
}

const requeue = async (): Promise<void> => {
  if (!deckId.value) {
    notificationStore.error('No deck selected')
    router.push({
      name: 'GameCreate',
      params: { slug: titleSlug.value }
    })
    return
  }

  try {
    requeueing.value = true
    await axios.post('/gameplay/matchmaking/queue/', {
      deck_id: parseInt(deckId.value),
      ladder_type: ladderType.value
    })
    notificationStore.success(`Requeued for ${ladderLabel.value} ranked match!`)

    // Reset state
    timedOut.value = false
    elapsedSeconds.value = 0
    inQueue.value = true

    // Restart polling and timer
    await fetchQueueStatus()
    startTimer()
    startPolling()
  } catch (err) {
    console.error('Error requeueing:', err)
    notificationStore.handleApiError(err as Error)
  } finally {
    requeueing.value = false
  }
}

const startTimer = (): void => {
  if (isDaily.value) return
  timerInterval.value = window.setInterval(() => {
    elapsedSeconds.value++

    // Check for timeout
    if (elapsedSeconds.value >= QUEUE_TIMEOUT_SECONDS) {
      timedOut.value = true
      stopTimer()
      stopPolling()
      leaveQueue() // Automatically leave the queue on timeout
    }
  }, 1000)
}

const stopTimer = (): void => {
  if (timerInterval.value !== null) {
    clearInterval(timerInterval.value)
    timerInterval.value = null
  }
}

const startPolling = (): void => {
  pollInterval.value = window.setInterval(async () => {
    await fetchQueueStatus()
  }, POLL_INTERVAL_MS)
}

const stopPolling = (): void => {
  if (pollInterval.value !== null) {
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }
}

// Watch for WebSocket connection status and ensure it's connected
watch(() => authStore.userWsStatus, (status) => {
  console.log('WebSocket status changed:', status)
  if (status === 'disconnected' && authStore.isAuthenticated) {
    console.log('WebSocket disconnected, attempting to reconnect...')
    authStore.connectUserWebSocket()
  }
})

// Lifecycle
onMounted(async () => {
  try {
    loading.value = true

    // Ensure WebSocket is connected for real-time match notifications
    if (authStore.isAuthenticated && authStore.userWsStatus !== 'connected') {
      console.log('Ensuring WebSocket connection for matchmaking...')
      authStore.connectUserWebSocket()
    }

    await fetchQueueStatus()

    if (inQueue.value) {
      startTimer()
      startPolling()
    } else {
      error.value = `You are not currently in the ${ladderLabel.value} queue`
    }
  } catch (err) {
    console.error('Error initializing ranked queue:', err)
    error.value = 'Failed to load queue status'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  stopTimer()
  stopPolling()
})
</script>

<style scoped>
.ranked-queue-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes ping {
  75%, 100% {
    transform: scale(2);
    opacity: 0;
  }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.animate-ping {
  animation: ping 1s cubic-bezier(0, 0, 0.2, 1) infinite;
}
</style>

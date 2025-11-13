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

      <main class="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 my-8">
        <div class="grid gap-8 lg:grid-cols-2">
          <!-- Left Panel: Play Ranked -->
          <Panel title="Play Ranked">
            <div class="space-y-4">
              <p class="text-sm text-gray-600 dark:text-gray-400">
                Queue for a ranked match and test your skills against other players.
                Winning ranked matches will increase your ELO rating.
              </p>

              <!-- Deck Selection for Ranked -->
              <div class="space-y-3">
                <h3 class="text-sm font-medium text-gray-900 dark:text-white">Choose Your Deck</h3>

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

                <div v-else class="space-y-2">
                  <div
                    v-for="deck in playerDecks"
                    :key="deck.id"
                    @click="selectedRankedDeck = deck"
                    :class="[
                      'cursor-pointer rounded-lg border-2 p-3 transition-colors',
                      selectedRankedDeck?.id === deck.id
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-gray-200 hover:border-primary-300 dark:border-gray-700'
                    ]"
                  >
                    <div class="flex items-center space-x-3">
                      <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-100 text-sm font-bold text-primary-600">
                        {{ deck.hero.name.charAt(0) }}
                      </div>
                      <div class="flex-1">
                        <div class="font-medium text-gray-900 dark:text-white">{{ deck.name }}</div>
                        <div class="text-xs text-gray-600">
                          {{ deck.hero.name }} • {{ deck.card_count }} cards
                        </div>
                      </div>
                      <div v-if="selectedRankedDeck?.id === deck.id" class="text-primary-600">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Play Ranked Button -->
              <button
                @click="queueForRanked"
                :disabled="!selectedRankedDeck || queuingForRanked"
                :class="[
                  'w-full inline-flex items-center justify-center rounded-lg px-6 py-3 text-sm font-medium transition-colors',
                  selectedRankedDeck && !queuingForRanked
                    ? 'bg-green-600 text-white hover:bg-green-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                ]"
              >
                {{ queuingForRanked ? 'Queueing...' : 'Play Ranked' }}
              </button>
            </div>
          </Panel>

          <!-- Right Panel: Play a Friend -->
          <Panel title="Play a Friend">
            <div class="space-y-4">
              <p class="text-sm text-gray-600 dark:text-gray-400">
                Challenge your friends to an unranked friendly match.
                These games won't affect your ELO rating.
              </p>

              <!-- Divider -->
              <div class="flex items-center justify-center py-2">
                <div class="text-sm text-gray-500 dark:text-gray-400">- or -</div>
              </div>

              <!-- Friends List -->
              <div class="space-y-3">
                <h3 class="text-sm font-medium text-gray-900 dark:text-white">Your Friends</h3>

                <div v-if="friendsLoading" class="text-center py-8">
                  <p class="text-gray-600">Loading your friends...</p>
                </div>

                <div v-else-if="friends.length === 0" class="text-center py-8">
                  <p class="text-gray-600 mb-4">You don't have any friends yet.</p>
                  <router-link
                    :to="{ name: 'Friends' }"
                    class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                  >
                    Add Friends
                  </router-link>
                </div>

                <div v-else class="space-y-2">
                  <div
                    v-for="friend in friends"
                    :key="friend.id"
                    class="flex items-center justify-between rounded-lg border border-gray-200 p-3 dark:border-gray-700"
                  >
                    <div class="flex items-center space-x-3">
                      <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary-100 text-sm font-bold text-secondary-600">
                        {{ (friend.friend.username || friend.friend.email).charAt(0).toUpperCase() }}
                      </div>
                      <div>
                        <div class="font-medium text-gray-900 dark:text-white">
                          {{ friend.friend.username || friend.friend.email }}
                        </div>
                      </div>
                    </div>
                    <button
                      @click="challengeFriend(friend)"
                      class="inline-flex items-center rounded-lg bg-secondary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-secondary-700"
                    >
                      Challenge
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </Panel>
        </div>

        <!-- Back Button -->
        <div class="mt-8 flex justify-center">
          <router-link
            :to="{ name: 'Title', params: { slug: titleSlug } }"
            class="inline-flex items-center rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            Back to Title
          </router-link>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTitleStore } from '../stores/title'
import { useNotificationStore } from '../stores/notifications'
import { matchmakingApi } from '../services/matchmaking'
import { friendsApi } from '../services/friends'
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

interface FriendData {
  id: number
  user: {
    id: number
    email: string
    username?: string
  }
  friend: {
    id: number
    email: string
    username?: string
  }
  status: string
}

const route = useRoute()
const router = useRouter()
const titleStore = useTitleStore()
const notificationStore = useNotificationStore()

// Component state
const loading = ref<boolean>(true)
const error = ref<string | null>(null)
const queuingForRanked = ref<boolean>(false)

// Data
const playerDecks = ref<DeckData[]>([])
const friends = ref<FriendData[]>([])
const playerDecksLoading = ref<boolean>(false)
const friendsLoading = ref<boolean>(false)

// Selections
const selectedRankedDeck = ref<DeckData | null>(null)

// Computed
const title = computed((): TitleData | null => titleStore.currentTitle)
const titleSlug = computed(() => route.params.slug as string)

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

const fetchFriends = async (): Promise<void> => {
  try {
    friendsLoading.value = true
    const response = await friendsApi.getFriendships()
    // Filter only accepted friendships
    friends.value = response.filter((f: FriendData) => f.status === 'accepted')
  } catch (err) {
    console.error('Error fetching friends:', err)
    error.value = 'Failed to load friends'
  } finally {
    friendsLoading.value = false
  }
}

const queueForRanked = async (): Promise<void> => {
  if (!selectedRankedDeck.value) return

  try {
    queuingForRanked.value = true

    const response = await matchmakingApi.queueForRankedMatch({
      title_slug: titleSlug.value,
      deck_id: selectedRankedDeck.value.id
    })

    notificationStore.success(response.message || 'Successfully queued for ranked match!')

    // TODO: Navigate to a queue/waiting screen or show a modal
    // For now, just show success and stay on the page
    console.log('Queue response:', response)
  } catch (err) {
    console.error('Error queueing for ranked:', err)
    notificationStore.handleApiError(err as Error)
  } finally {
    queuingForRanked.value = false
  }
}

const challengeFriend = (friend: FriendData): void => {
  // TODO: Implement friend challenge functionality
  // This will be implemented in a future task
  notificationStore.info(`Challenge feature coming soon! You want to challenge ${friend.friend.username || friend.friend.email}`)
  console.log('Challenge friend:', friend)
}

// Lifecycle
onMounted(async () => {
  try {
    loading.value = true

    // Fetch player decks and friends
    await Promise.all([
      fetchPlayerDecks(),
      fetchFriends()
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
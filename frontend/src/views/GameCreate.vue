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
        <h1 class="font-display text-4xl font-bold text-gray-900 dark:text-gray-900">NEW GAME</h1>
      </section>

      <main class="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 my-8">
        <!-- Game Mode Toggle -->
        <div class="mb-8">
          <div class="flex justify-center">
            <div class="inline-flex rounded-lg border border-gray-200 bg-white p-1 dark:border-gray-700 dark:bg-gray-800">
              <button
                @click="gameMode = 'pvp'"
                :class="[
                  'rounded-md px-6 py-2 text-sm font-medium transition-colors',
                  gameMode === 'pvp'
                    ? 'bg-secondary-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                ]"
              >
                ⚔️ vs Player
              </button>
              <button
                @click="gameMode = 'pve'"
                :class="[
                  'rounded-md px-6 py-2 text-sm font-medium transition-colors',
                  gameMode === 'pve'
                    ? 'bg-secondary-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                ]"
              >
                🤖 vs AI
              </button>

            </div>
          </div>
        </div>

        <div class="grid gap-8 md:grid-cols-2">
          <!-- Player Deck Selection -->
          <Panel title="Your Deck">
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
                v-if="selectedPlayerDeck && !showAllPlayerDecks"
                class="rounded-lg border-2 border-secondary-500 bg-secondary-50 p-4 dark:bg-secondary-900/20"
              >
                <div class="flex items-center space-x-3">
                  <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary-100 text-sm font-bold text-secondary-600">
                    {{ selectedPlayerDeck.hero.name.charAt(0) }}
                  </div>
                  <div class="flex-1">
                    <div class="font-medium text-gray-900 dark:text-white">{{ selectedPlayerDeck.name }}</div>
                    <div class="text-sm text-gray-600">
                      {{ selectedPlayerDeck.hero.name }} • {{ selectedPlayerDeck.card_count }} cards
                    </div>
                  </div>
                  <div class="text-secondary-600">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                  </div>
                </div>
              </div>

              <div v-else>
                <div
                  v-for="deck in playerDecks"
                  :key="deck.id"
                  @click="selectPlayerDeck(deck)"
                  :class="[
                    'cursor-pointer rounded-lg border-2 p-4 transition-colors',
                    selectedPlayerDeck?.id === deck.id
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
                        {{ deck.hero.name }} • {{ deck.card_count }} cards
                      </div>
                    </div>
                    <div v-if="selectedPlayerDeck?.id === deck.id" class="text-secondary-600">
                      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                      </svg>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="playerDecks.length > 1" class="pt-2 text-center">
                <button
                  type="button"
                  class="text-sm font-medium text-secondary-600 hover:text-secondary-700"
                  @click="showAllPlayerDecks = !showAllPlayerDecks"
                >
                  {{ showAllPlayerDecks ? 'Hide decks' : 'View all decks' }}
                </button>
              </div>
            </div>
          </Panel>

          <!-- Opponent Deck Selection -->
          <Panel :title="gameMode === 'pve' ? 'Choose AI Opponent' : ''">
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
              <div v-if="friendsLoading" class="text-center py-8">
                <p class="text-gray-600">Loading friends...</p>
              </div>

              <div v-else class="space-y-6">
                <div class="flex flex-col items-center space-y-3">
                  <div class="flex w-full flex-col gap-3 sm:w-auto sm:flex-row sm:justify-center">
                    <button
                      type="button"
                      class="inline-flex w-full items-center justify-center rounded-lg px-6 py-3 text-sm font-semibold transition-colors sm:w-auto"
                      :class="[
                        isRankedButtonDisabled
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          : 'bg-primary-600 text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2'
                      ]"
                      :disabled="isRankedButtonDisabled"
                      @click="queueForRanked('rapid')"
                    >
                      Play Rapid (1 min)
                    </button>
                    <button
                      type="button"
                      class="inline-flex w-full items-center justify-center rounded-lg px-6 py-3 text-sm font-semibold transition-colors sm:w-auto"
                      :class="[
                        isRankedButtonDisabled
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          : 'bg-secondary-600 text-white hover:bg-secondary-700 focus:outline-none focus:ring-2 focus:ring-secondary-500 focus:ring-offset-2'
                      ]"
                      :disabled="isRankedButtonDisabled"
                      @click="queueForRanked('daily')"
                    >
                      Play Daily (24h)
                    </button>
                  </div>
                  <p v-if="rankedQueueLoading" class="text-xs text-gray-500">
                    Checking ranked queue status...
                  </p>
                  <div v-else class="space-y-2 text-xs text-center text-gray-600">
                    <div v-if="rapidQueueEntry" class="flex flex-col items-center gap-1">
                      <div>
                        Rapid queued with {{ rapidQueueEntry.deck.name }}.
                      </div>
                      <div class="flex items-center gap-2">
                        <button
                          type="button"
                          class="text-primary-600 hover:text-primary-700"
                          @click="leaveRankedQueue('rapid')"
                        >
                          Leave queue
                        </button>
                        <router-link
                          :to="{
                            name: 'RankedQueue',
                            params: { slug: titleSlug },
                            query: { deck_id: rapidQueueEntry.deck.id, ladder_type: 'rapid' }
                          }"
                          class="text-gray-500 hover:text-gray-700"
                        >
                          View status
                        </router-link>
                      </div>
                    </div>
                    <div v-if="dailyQueueEntry" class="flex flex-col items-center gap-1">
                      <div>
                        Daily queued with {{ dailyQueueEntry.deck.name }}.
                      </div>
                      <div class="flex items-center gap-2">
                        <button
                          type="button"
                          class="text-primary-600 hover:text-primary-700"
                          @click="leaveRankedQueue('daily')"
                        >
                          Leave queue
                        </button>
                        <span class="text-gray-400">
                          You can leave this page and stay queued.
                        </span>
                      </div>
                    </div>
                  </div>
                  <p v-if="rankedQueueError" class="text-xs text-red-600 text-center">
                    {{ rankedQueueError }}
                  </p>
                  <div class="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    or
                  </div>
                </div>

                <div>
                  <div class="mb-4 text-center text-sm font-semibold text-gray-900 dark:text-white">Play a Friend</div>

                  <div v-if="friendsError" class="rounded-lg border border-red-200 bg-red-50 p-4 text-center text-sm text-red-600">
                    {{ friendsError }}
                  </div>

                  <div v-else-if="friends.length === 0" class="rounded-lg border border-gray-200 bg-white p-6 text-center text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800">
                    You don't have any friends yet. Add a friend to challenge them here.
                  </div>

                  <div v-else class="space-y-3">
                    <div
                      v-for="friend in friends"
                      :key="friend.id"
                      class="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800"
                    >
                      <div>
                        <div class="font-medium text-gray-900 dark:text-white">
                          {{ friend.friend_data.display_name || friend.friend_data.username || friend.friend_data.email }}
                        </div>
                        <div class="text-sm text-gray-600 dark:text-gray-400">
                          {{ friend.friend_data.email }}
                        </div>
                      </div>
                      <button
                        type="button"
                        class="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2"
                        :class="[
                          isFriendChallenged(friend)
                            ? 'border-gray-300 text-gray-400 cursor-not-allowed'
                            : 'border-secondary-500 text-secondary-600 hover:bg-secondary-50 focus:ring-secondary-500'
                        ]"
                        :disabled="isFriendChallenged(friend)"
                        @click="challengeFriend(friend)"
                      >
                        {{ isFriendChallenged(friend) ? 'Challenged' : 'Challenge' }}
                      </button>
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
import { useNotificationStore } from '../stores/notifications'
import axios from '../config/api'
import Panel from '../components/layout/Panel.vue'
import { friendsApi } from '../services/friends'
import type { Friendship } from '../types/auth'
import { challengesApi } from '../services/challenges'
import type { FriendlyChallenge, PendingChallengesResponse } from '../types/challenge'
import type { LadderType } from '../types/game'

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

interface RankedQueueEntry {
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

// Component state
const loading = ref<boolean>(true)
const error = ref<string | null>(null)
const creating = ref<boolean>(false)
const queueingRanked = ref<boolean>(false)
const gameMode = ref<'pve' | 'pvp'>('pvp')

// Data
const playerDecks = ref<DeckData[]>([])
const pveDecks = ref<DeckData[]>([])
const playerDecksLoading = ref<boolean>(false)
const pveDecksLoading = ref<boolean>(false)
const friends = ref<Friendship[]>([])
const friendsLoading = ref<boolean>(false)
const friendsError = ref<string | null>(null)
const rapidQueueEntry = ref<RankedQueueEntry | null>(null)
const dailyQueueEntry = ref<RankedQueueEntry | null>(null)
const rankedQueueLoading = ref<boolean>(false)
const rankedQueueError = ref<string | null>(null)
// Friendly challenges (outgoing only - incoming handled on Title page)
const pendingOutgoingChallenges = ref<FriendlyChallenge[]>([])
const showAllPlayerDecks = ref<boolean>(true)
const lastUsedDeckId = ref<number | null>(null)

// Selections
const selectedPlayerDeck = ref<DeckData | null>(null)
const selectedOpponentDeck = ref<DeckData | null>(null)

// Computed
const titleSlug = computed(() => route.params.slug as string)

const canCreateGame = computed(() => {
  if (gameMode.value === 'pve') {
    return !!selectedPlayerDeck.value && !!selectedOpponentDeck.value && !creating.value
  }

  return false
})

const hasQueueEntry = computed(() => !!rapidQueueEntry.value || !!dailyQueueEntry.value)

const isRankedButtonDisabled = computed(() => {
  return queueingRanked.value || rankedQueueLoading.value || hasQueueEntry.value
})

const outgoingPendingByUserId = computed<Record<number, boolean>>(() => {
  const map: Record<number, boolean> = {}
  for (const c of pendingOutgoingChallenges.value) {
    // Disable by the challengee's user id
    map[c.challengee.id] = true
  }
  return map
})

const initializePlayerDeckSelection = (): void => {
  if (playerDecks.value.length === 0) return

  if (playerDecks.value.length === 1) {
    selectedPlayerDeck.value = playerDecks.value[0]
    showAllPlayerDecks.value = false
    return
  }

  const storedDeck = playerDecks.value.find(deck => deck.id === lastUsedDeckId.value)
  if (storedDeck) {
    selectedPlayerDeck.value = storedDeck
    showAllPlayerDecks.value = false
  } else if (!selectedPlayerDeck.value) {
    showAllPlayerDecks.value = true
  }
}

const selectPlayerDeck = (deck: DeckData): void => {
  selectedPlayerDeck.value = deck
  if (playerDecks.value.length > 1) {
    showAllPlayerDecks.value = false
  }
}

// Methods
const fetchPlayerDecks = async (): Promise<void> => {
  try {
    playerDecksLoading.value = true
    const response = await axios.get(`/collection/titles/${titleSlug.value}/decks/`)
    playerDecks.value = response.data.decks || []
    lastUsedDeckId.value = response.data.last_used_deck_id ?? null
    initializePlayerDeckSelection()
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

const fetchFriends = async (): Promise<void> => {
  try {
    friendsLoading.value = true
    friendsError.value = null

    const friendships = await friendsApi.getFriendships()
    friends.value = friendships.filter(friendship => friendship.status === 'accepted')
  } catch (err) {
    console.error('Error fetching friends:', err)
    friendsError.value = 'Failed to load friends. Please try again later.'
  } finally {
    friendsLoading.value = false
  }
}

const fetchPendingChallenges = async (): Promise<void> => {
  try {
    const resp: PendingChallengesResponse = await challengesApi.listPending(titleSlug.value)
    pendingOutgoingChallenges.value = resp.outgoing || []
  } catch (err) {
    console.error('Error fetching pending challenges:', err)
  }
}

const fetchRankedQueueStatus = async (ladderType: LadderType): Promise<void> => {
  if (!titleSlug.value) return

  try {
    rankedQueueLoading.value = true
    rankedQueueError.value = null
    const response = await axios.get(`/gameplay/matchmaking/status/${titleSlug.value}/`, {
      params: { ladder_type: ladderType }
    })
    const entry = response.data.in_queue ? response.data.queue_entry : null
    if (ladderType === 'rapid') {
      rapidQueueEntry.value = entry
    } else {
      dailyQueueEntry.value = entry
    }
  } catch (err) {
    console.error('Error fetching ranked queue status:', err)
    rankedQueueError.value = 'Failed to check ranked queue status.'
  } finally {
    rankedQueueLoading.value = false
  }
}

const fetchAllRankedQueueStatus = async (): Promise<void> => {
  await Promise.all([fetchRankedQueueStatus('rapid'), fetchRankedQueueStatus('daily')])
}

const leaveRankedQueue = async (ladderType: LadderType): Promise<void> => {
  try {
    await axios.post(`/gameplay/matchmaking/leave/${titleSlug.value}/`, null, {
      params: { ladder_type: ladderType }
    })
    notificationStore.success(`Left ${ladderType} ranked queue`)
    await fetchAllRankedQueueStatus()
  } catch (err) {
    console.error('Error leaving queue:', err)
    notificationStore.handleApiError(err as Error)
  }
}

const queueForRanked = async (ladderType: LadderType): Promise<void> => {
  if (!selectedPlayerDeck.value) {
    notificationStore.error('Please select a deck first')
    return
  }

  try {
    queueingRanked.value = true
    const response = await axios.post('/gameplay/matchmaking/queue/', {
      deck_id: selectedPlayerDeck.value.id,
      ladder_type: ladderType
    })
    const ladderLabel = ladderType === 'daily' ? 'daily' : 'rapid'
    notificationStore.success(`Queued for ${ladderLabel} ranked match! Waiting for opponent...`)
    console.log('Queue response:', response.data)

    if (ladderType === 'rapid') {
      // Navigate to the ranked queue waiting screen
      router.push({
        name: 'RankedQueue',
        params: { slug: titleSlug.value },
        query: { deck_id: selectedPlayerDeck.value.id, ladder_type: ladderType }
      })
    } else {
      await fetchAllRankedQueueStatus()
    }
  } catch (err) {
    console.error('Error queueing for ranked:', err)
    notificationStore.handleApiError(err as Error)
    const errorResponse = (err as any)?.response
    if (errorResponse?.status === 400 && errorResponse?.data?.queue_entry_id) {
      const queuedLadder = (errorResponse.data?.ladder_type as LadderType) || 'rapid'
      if (queuedLadder === 'rapid') {
        // User is already in queue, navigate to waiting screen
        router.push({
          name: 'RankedQueue',
          params: { slug: titleSlug.value },
          query: { deck_id: selectedPlayerDeck.value.id, ladder_type: queuedLadder }
        })
      } else {
        await fetchAllRankedQueueStatus()
      }
    }
  } finally {
    queueingRanked.value = false
  }
}

const isFriendChallenged = (friend: Friendship): boolean => {
  const friendUserId = friend.friend_data.id as unknown as number
  return !!outgoingPendingByUserId.value[friendUserId]
}

const challengeFriend = async (friend: Friendship): Promise<void> => {
  const friendUserId = (friend.friend_data.id as unknown as number) || friend.friend
  if (!selectedPlayerDeck.value) {
    notificationStore.error('Please select your deck first')
    return
  }
  try {
    await challengesApi.createChallenge({
      title_slug: titleSlug.value,
      challengee_user_id: friendUserId,
      challenger_deck_id: selectedPlayerDeck.value.id
    })
    notificationStore.success('Challenge sent!')
    // Refresh pending list so button greys out
    await fetchPendingChallenges()
  } catch (err) {
    console.error('Error creating challenge:', err)
    notificationStore.handleApiError(err as Error)
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

  // Load friends if switching to PvP and not already loaded
  if (newMode === 'pvp' && friends.value.length === 0 && !friendsLoading.value) {
    fetchFriends()
  }

  if (newMode === 'pvp') {
    fetchAllRankedQueueStatus()
    fetchPendingChallenges()
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

    // Load friends if initial mode is PvP (watcher only fires on change)
    if (gameMode.value === 'pvp') {
      await fetchFriends()
    }

    await fetchAllRankedQueueStatus()
    // Preload challenges if user lands with PvP selected later
    await fetchPendingChallenges()
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

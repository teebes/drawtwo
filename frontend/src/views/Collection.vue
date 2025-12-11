<template>
  <div class="collection-page min-h-screen bg-gray-50 dark:bg-gray-900">

    <div v-if="!loading && !error && title" class="relative flex flex-col h-full">
      <!-- Hero Section -->
      <section class="banner">
        <h1>Collection</h1>
      </section>

      <!-- Cards Sections -->
      <main class="mx-auto w-full px-4 sm:px-6 lg:px-8 pb-16 space-y-12">
        <!-- Decks Section -->
        <section class="max-w-xl mx-auto mt-8">
          <Panel title="Your Decks">
            <div v-if="decks.length > 0" class="space-y-3 flex-grow">
              <router-link
                v-for="deck in decks"
                :key="deck.id"
                :to="{ name: 'DeckDetail', params: { id: deck.id } }"
                class="flex items-center justify-between rounded-lg bg-gray-50 p-3 hover:bg-gray-100 transition-colors dark:bg-gray-800 dark:hover:bg-gray-700"
              >
                <div class="flex items-center space-x-3">
                  <div
                    class="relative w-10 max-w-[4rem] rounded-lg overflow-hidden shadow-md bg-gray-200 dark:bg-gray-700 flex items-center justify-center border border-gray-200 dark:border-gray-600"
                    style="aspect-ratio: 5 / 7;"
                  >
                    <img
                      v-if="deck.hero.art_url"
                      :src="deck.hero.art_url"
                      :alt="`${deck.hero.name} hero art`"
                      class="inset-0 h-full object-contain object-center border-gray-600 border-2 rounded-lg"
                    />
                    <span v-else class="text-lg font-semibold text-primary-600">
                      {{ deck.hero.name.charAt(0) }}
                    </span>
                  </div>
                  <div>
                    <div class="font-medium text-gray-900 hover:text-primary-600 dark:text-white">
                      {{ deck.name }}
                    </div>
                  </div>
                </div>
                <div class="text-sm text-gray-500 dark:text-gray-400 font-medium">
                  {{ deck.card_count }} {{ deck.card_count === 1 ? 'card' : 'cards' }}
                </div>
              </router-link>

              <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
                <router-link
                  :to="{ name: 'DeckCreate', params: { slug: title.slug } }"
                  class="flex items-center justify-center w-full rounded-lg border-2 border-dashed border-gray-300 p-3 text-sm font-medium text-gray-600 hover:border-primary-400 hover:text-primary-600 transition-colors"
                >
                  <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                  </svg>
                  New Deck
                </router-link>
              </div>
            </div>

            <div v-else class="text-center py-8">
              <p class="text-gray-600 mb-4 dark:text-gray-400">You don't have any decks for this title yet.</p>
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
              <p class="text-gray-600 dark:text-gray-400">Loading decks...</p>
            </div>
          </Panel>
        </section>

        <!-- Filters -->
        <section v-if="!cardsLoading && cards.length > 0" class="top-0 z-10 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-4 backdrop-blur supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-gray-900/60">
          <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
            <div class="space-y-2">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Type:</span>
                <div class="inline-flex rounded-md shadow-sm overflow-hidden border border-gray-200 dark:border-gray-700">
                  <button
                    type="button"
                    class="px-3 py-1.5 text-sm font-medium focus:outline-none"
                    :class="[
                      typeFilter === 'all' ? 'bg-secondary-500 text-white' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700',
                    ]"
                    @click="typeFilter = 'all'"
                  >All</button>
                  <button
                    type="button"
                    class="px-3 py-1.5 text-sm font-medium border-l border-gray-200 dark:border-gray-700 focus:outline-none"
                    :class="[
                      typeFilter === 'creature' ? 'bg-secondary-500 text-white' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700',
                    ]"
                    @click="typeFilter = 'creature'"
                  >Creatures</button>
                  <button
                    type="button"
                    class="px-3 py-1.5 text-sm font-medium border-l border-gray-200 dark:border-gray-700 focus:outline-none"
                    :class="[
                      typeFilter === 'spell' ? 'bg-secondary-500 text-white' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700',
                    ]"
                    @click="typeFilter = 'spell'"
                  >Spells</button>
                </div>
              </div>
            </div>

            <!-- <div class="flex flex-wrap items-end gap-4">
              <div class="flex flex-col">
                <label class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Min Cost</label>
                <select
                  class="rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:ring-primary-600 focus:border-primary-600"
                  v-model="minCostStr"
                >
                  <option value="">Any</option>
                  <option v-for="n in 11" :key="'min-'+(n-1)" :value="String(n-1)">{{ n-1 }}</option>
                </select>
              </div>
              <div class="flex flex-col">
                <label class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Max Cost</label>
                <select
                  class="rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:ring-primary-600 focus:border-primary-600"
                  v-model="maxCostStr"
                >
                  <option value="">Any</option>
                  <option v-for="n in 11" :key="'max-'+(n-1)" :value="String(n-1)">{{ n-1 }}</option>
                </select>
              </div>

              <button
                type="button"
                class="inline-flex items-center rounded-md border border-gray-300 dark:border-gray-700 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                @click="clearFilters"
              >
                Clear
              </button>
            </div> -->
          </div>
        </section>
        <div v-if="cardsLoading" class="text-center py-12">
          <p class="text-gray-600 dark:text-gray-400">Loading cards...</p>
        </div>

        <div v-else-if="cards.length === 0" class="text-center py-12">
          <p class="text-gray-600 dark:text-gray-400">No cards found for this title.</p>
        </div>

        <div v-else>
          <!-- Common Cards Section -->
          <section v-if="commonCards.length > 0" class="mt-4">
            <h2 class="font-display text-2xl font-bold text-gray-900 dark:text-white mb-6">
              Common Cards
            </h2>
            <div class="grid md:gap-12 sm:gap-10 gap-8 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
              <div
                v-for="card in commonCards"
                :key="card.slug"
                class="relative group"
              >
                <GameCard
                  :card="card"
                  :details="true"
                  class="cursor-pointer"
                  @click="navigateToDetails(card.slug)" />
                <div v-if="0" class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    @click.stop="navigateToDetails(card.slug)"
                    class="inline-flex items-center rounded-full bg-white dark:bg-gray-800 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 shadow-sm hover:shadow-md transition-all"
                    title="View card details"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M1.458 12C2.732 7.943 6.73 5 12 5s9.268 2.943 10.542 7c-1.274 4.057-5.272 7-10.542 7S2.732 16.057 1.458 12z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </section>

          <!-- Faction Cards Sections -->
          <section
            v-for="[factionName, factionCards] in factionCardGroups"
            :key="factionName"
            class="space-y-6 mt-8"
          >
            <h2 class="font-display text-2xl font-bold text-gray-900 dark:text-white capitalize">
              {{ factionName }} Cards
            </h2>
            <div class="grid md:gap-12 sm:gap-10 gap-8 grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              <div
                v-for="card in factionCards"
                :key="card.slug"
                class="relative group"
              >
                <GameCard
                  :card="card"
                  :class="canEditTitle ? 'cursor-pointer' : ''"
                  @click="canEditTitle ? navigateToEdit(card.slug) : null" />
                <div
                  v-if="canEditTitle"
                  class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <button
                    @click.stop="navigateToEdit(card.slug)"
                    class="inline-flex items-center rounded-full bg-white dark:bg-gray-800 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 shadow-sm hover:shadow-md transition-all"
                    title="Edit card"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </section>

          <!-- Uncollectible Cards Section -->
          <section v-if="uncollectibleCards.length > 0" class="mt-24">
            <h2 class="font-display text-2xl font-bold text-gray-900 dark:text-white mb-6">
              Uncollectible Cards
            </h2>

            <!-- Uncollectible Common Cards -->
            <div v-if="uncollectibleCommonCards.length > 0" class="mb-8">
              <h3 class="font-display text-xl font-semibold text-gray-800 dark:text-gray-200 mb-4">
                Common
              </h3>
              <div class="grid md:gap-12 sm:gap-10 gap-8 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
                <div
                  v-for="card in uncollectibleCommonCards"
                  :key="card.slug"
                  class="relative group"
                >
                  <GameCard
                    :card="card"
                    :details="true"
                    class="cursor-pointer opacity-75"
                    @click="navigateToDetails(card.slug)" />
                </div>
              </div>
            </div>

            <!-- Uncollectible Faction Cards -->
            <div
              v-for="[factionName, factionCards] in uncollectibleFactionCardGroups"
              :key="factionName"
              class="space-y-6 mb-8"
            >
              <h3 class="font-display text-xl font-semibold text-gray-800 dark:text-gray-200 capitalize">
                {{ factionName }}
              </h3>
              <div class="grid md:gap-12 sm:gap-10 gap-8 grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                <div
                  v-for="card in factionCards"
                  :key="card.slug"
                  class="relative group"
                >
                  <GameCard
                    :card="card"
                    :class="canEditTitle ? 'cursor-pointer opacity-75' : 'opacity-75'"
                    @click="canEditTitle ? navigateToEdit(card.slug) : null" />
                  <div
                    v-if="canEditTitle"
                    class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <button
                      @click.stop="navigateToEdit(card.slug)"
                      class="inline-flex items-center rounded-full bg-white dark:bg-gray-800 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 shadow-sm hover:shadow-md transition-all"
                      title="Edit card"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>

      <section v-if="canEditTitle" class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-1 mb-8">
        <router-link
              :to="{ name: 'CardCreate', params: { slug: title.slug } }"
              class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
              </svg>
              Create New Card
            </router-link>
      </section>

    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center min-h-screen">
      <p class="text-gray-600 dark:text-gray-400">Loading title...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="flex items-center justify-center min-h-screen">
      <div class="text-center">
        <p class="text-red-600 dark:text-red-400 mb-4">{{ error }}</p>
        <router-link
          to="/"
          class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Go Home
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useTitleStore } from '../stores/title'
import axios from '../config/api'
import GameCard from '../components/game/GameCard.vue'
import Panel from '../components/layout/Panel.vue'
import type { Card } from '../types/card'

interface TitleData {
  id: number
  slug: string
  version: number
  is_latest: boolean
  name: string
  description: string
  author: number
  author_username: string
  status: 'draft' | 'published' | 'archived'
  published_at: string | null
  created_at: string
  updated_at: string
  can_edit?: boolean  // Optional since it's only present when user is authenticated
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const titleStore = useTitleStore()

// Use the title from the store instead of local state
const title = computed(() => titleStore.currentTitle as TitleData | null)
const loading = computed(() => titleStore.loading)
const error = computed(() => titleStore.error)

const cards = ref<Card[]>([])
const cardsLoading = ref<boolean>(false)

// Deck management
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

const decks = ref<DeckData[]>([])
const decksLoading = ref<boolean>(false)

// Filters
const typeFilter = ref<'all' | 'creature' | 'spell'>('all')
const minCostStr = ref<string>('')
const maxCostStr = ref<string>('')

const minCost = computed<number | null>(() => {
  if (minCostStr.value === '') return null
  const val = parseInt(minCostStr.value, 10)
  return Number.isNaN(val) ? null : val
})
const maxCost = computed<number | null>(() => {
  if (maxCostStr.value === '') return null
  const val = parseInt(maxCostStr.value, 10)
  return Number.isNaN(val) ? null : val
})

const filteredCards = computed<Card[]>(() => {
  if (minCost.value !== null && maxCost.value !== null && minCost.value > maxCost.value) {
    return []
  }

  return cards.value.filter((card) => {
    if (typeFilter.value !== 'all' && card.card_type !== typeFilter.value) {
      return false
    }
    if (minCost.value !== null && card.cost < minCost.value) {
      return false
    }
    if (maxCost.value !== null && card.cost > maxCost.value) {
      return false
    }
    return true
  })
})

// Computed properties for organizing cards by faction
// Filter to only show collectible cards (default to true if not present)
const collectibleCards = computed(() => {
  return filteredCards.value.filter(card => card.is_collectible !== false)
})

const uncollectibleCards = computed(() => {
  return filteredCards.value.filter(card => card.is_collectible === false)
})

const commonCards = computed(() => {
  return collectibleCards.value.filter(card => !card.faction)
})

const factionCardGroups = computed(() => {
  const factionGroups = new Map<string, Card[]>()

  collectibleCards.value.forEach(card => {
    if (card.faction) {
      if (!factionGroups.has(card.faction)) {
        factionGroups.set(card.faction, [])
      }
      factionGroups.get(card.faction)!.push(card)
    }
  })

  // Sort faction groups alphabetically
  return Array.from(factionGroups.entries()).sort(([a], [b]) => a.localeCompare(b))
})

// Organize uncollectible cards by faction
const uncollectibleCommonCards = computed(() => {
  return uncollectibleCards.value.filter(card => !card.faction)
})

const uncollectibleFactionCardGroups = computed(() => {
  const factionGroups = new Map<string, Card[]>()

  uncollectibleCards.value.forEach(card => {
    if (card.faction) {
      if (!factionGroups.has(card.faction)) {
        factionGroups.set(card.faction, [])
      }
      factionGroups.get(card.faction)!.push(card)
    }
  })

  // Sort faction groups alphabetically
  return Array.from(factionGroups.entries()).sort(([a], [b]) => a.localeCompare(b))
})

// Check if user can edit this title
const canEditTitle = computed(() => {
  return authStore.isAuthenticated &&
         title.value &&
         title.value.can_edit === true
})

const navigateToDetails = (cardSlug: string): void => {
  router.push({
    name: 'CardDetails',
    params: {
      slug: title.value?.slug,
      cardSlug
    }
  })
}

const navigateToEdit = (cardSlug: string): void => {
  router.push({
    name: 'CardEdit',
    params: {
      slug: title.value?.slug,
      cardSlug
    }
  })
}

// Title data now comes from the store via router preloading

const fetchCards = async (): Promise<void> => {
  if (!title.value) return

  try {
    cardsLoading.value = true
    const slug = route.params.slug as string
    const response = await axios.get(`/titles/${slug}/cards/`)
    cards.value = response.data || []
  } catch (err) {
    console.error('Error fetching cards:', err)
    // Don't set error for cards if title loaded successfully
    // Just log it and show empty state
  } finally {
    cardsLoading.value = false
  }
}

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

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

// Watch for title to be loaded and then fetch cards and decks
watch(title, async (newTitle) => {
  if (newTitle) {
    await Promise.all([
      fetchCards(),
      fetchDecks()
    ])
  }
}, { immediate: true })

onMounted(() => {
  // Title will be loaded by router, so we just need to watch for it
})
</script>

<style scoped>
.collection-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>

<template>
  <div class="title-cards-page min-h-screen bg-gray-50 dark:bg-gray-900">

    <div v-if="!loading && !error && title" class="relative flex flex-col h-full">
      <!-- Hero Section -->
      <section class="page-banner">
        <h1 class="font-display text-4xl font-bold text-white">Collection</h1>
      </section>


      <!-- Cards Sections -->
      <main class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-16 space-y-12">
        <!-- Filters -->
        <section v-if="!cardsLoading && cards.length > 0" class="sticky top-0 z-10 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-4 backdrop-blur supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-gray-900/60">
          <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
            <div class="space-y-2">
              <div class="text-sm text-gray-600 dark:text-gray-400">
                Showing {{ filteredCards.length }} of {{ cards.length }} cards
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Type:</span>
                <div class="inline-flex rounded-md shadow-sm overflow-hidden border border-gray-200 dark:border-gray-700">
                  <button
                    type="button"
                    class="px-3 py-1.5 text-sm font-medium focus:outline-none"
                    :class="[
                      typeFilter === 'all' ? 'bg-primary-600 text-white' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700',
                    ]"
                    @click="typeFilter = 'all'"
                  >All</button>
                  <button
                    type="button"
                    class="px-3 py-1.5 text-sm font-medium border-l border-gray-200 dark:border-gray-700 focus:outline-none"
                    :class="[
                      typeFilter === 'minion' ? 'bg-primary-600 text-white' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700',
                    ]"
                    @click="typeFilter = 'minion'"
                  >Minions</button>
                  <button
                    type="button"
                    class="px-3 py-1.5 text-sm font-medium border-l border-gray-200 dark:border-gray-700 focus:outline-none"
                    :class="[
                      typeFilter === 'spell' ? 'bg-primary-600 text-white' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700',
                    ]"
                    @click="typeFilter = 'spell'"
                  >Spells</button>
                </div>
              </div>
            </div>

            <div class="flex flex-wrap items-end gap-4">
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
            </div>
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
            <div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              <div
                v-for="card in commonCards"
                :key="card.slug"
                class="relative group"
              >
                <CollectionCard
                  :card="card"
                  heightMode="fixed"
                  height="md"
                  :class="canEditTitle ? 'cursor-pointer transition-transform group-hover:scale-105' : ''"
                  @click="canEditTitle ? navigateToEdit(card.slug) : null"
                />
                <div
                  v-if="canEditTitle"
                  class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
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

          <!-- Faction Cards Sections -->
          <section
            v-for="[factionName, factionCards] in factionCardGroups"
            :key="factionName"
            class="space-y-6 mt-8"
          >
            <h2 class="font-display text-2xl font-bold text-gray-900 dark:text-white capitalize">
              {{ factionName }} Cards
            </h2>
            <div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              <div
                v-for="card in factionCards"
                :key="card.slug"
                class="relative group"
              >
                <CollectionCard
                  :card="card"
                  heightMode="auto"
                  :class="canEditTitle ? 'cursor-pointer transition-transform group-hover:scale-105' : ''"
                  @click="canEditTitle ? navigateToEdit(card.slug) : null"
                />
                <div
                  v-if="canEditTitle"
                  class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
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
        </div>
      </main>

      <!-- Bottom Bar -->
      <section v-if="canEditTitle"class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <div class="flex items-center justify-between">
          <div class="text-sm text-gray-600 dark:text-gray-400">
            {{ filteredCards.length }} / {{ cards.length }} Cards
          </div>

          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-600 dark:text-gray-400">
              Click on any card to edit it
            </span>
            <router-link
              :to="{ name: 'CardCreate', params: { slug: title.slug } }"
              class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
              </svg>
              Create New Card
            </router-link>
          </div>
        </div>
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
import { useAuthStore } from '../stores/auth.js'
import { useTitleStore } from '../stores/title.js'
import axios from '../config/api.js'
import CollectionCard from '../components/game/CollectionCard.vue'
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
const title = computed((): TitleData | null => titleStore.currentTitle)
const loading = computed(() => titleStore.loading)
const error = computed(() => titleStore.error)

const cards = ref<Card[]>([])
const cardsLoading = ref<boolean>(false)

// Filters
const typeFilter = ref<'all' | 'minion' | 'spell'>('all')
const minCostStr = ref<string>('')
const maxCostStr = ref<string>('')

const clearFilters = (): void => {
  typeFilter.value = 'all'
  minCostStr.value = ''
  maxCostStr.value = ''
}

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
const commonCards = computed(() => {
  return filteredCards.value.filter(card => !card.faction)
})

const factionCardGroups = computed(() => {
  const factionGroups = new Map<string, Card[]>()

  filteredCards.value.forEach(card => {
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

// Watch for title to be loaded and then fetch cards
watch(title, async (newTitle) => {
  if (newTitle) {
    await fetchCards()
  }
}, { immediate: true })

onMounted(() => {
  // Title will be loaded by router, so we just need to watch for it
})
</script>

<style scoped>
.title-cards-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
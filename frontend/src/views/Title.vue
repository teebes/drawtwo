<template>
  <div class="title-page">
    <AppHeader />

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
                  :to="{ name: 'DeckDetail', params: { id: 'new' } }"
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
                :to="{ name: 'DeckDetail', params: { id: 'new' } }"
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
            <div class="text-center py-8">
              <p class="text-gray-600 mb-4">Game functionality coming soon!</p>
              <button
                disabled
                class="inline-flex items-center rounded-lg bg-gray-300 px-4 py-2 text-sm font-medium text-gray-500 cursor-not-allowed"
              >
                Start Game
              </button>
            </div>
          </Panel>
        </div>
      </main>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from '../config/api.js'
import AppHeader from '../components/AppHeader.vue'
import Panel from '../components/layout/Panel.vue'

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
}

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

const route = useRoute()
const title = ref<TitleData | null>(null)
const decks = ref<DeckData[]>([])
const loading = ref<boolean>(true)
const decksLoading = ref<boolean>(false)
const error = ref<string | null>(null)

const fetchTitle = async (): Promise<void> => {
  try {
    const slug = route.params.slug as string
    const response = await axios.get(`/builder/titles/${slug}/`)
    title.value = response.data
  } catch (err) {
    if (err.response?.status === 404) {
      error.value = 'Title not found'
    } else {
      error.value = err.response?.data?.message || err.message || 'Failed to load title'
    }
    console.error('Error fetching title:', err)
  } finally {
    loading.value = false
  }
}

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

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

onMounted(async () => {
  await fetchTitle()
  if (title.value) {
    await fetchDecks()
  }
})
</script>

<style scoped>
.title-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
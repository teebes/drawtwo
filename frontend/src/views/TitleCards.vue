<template>
  <div class="title-cards-page min-h-screen bg-gray-50 dark:bg-gray-900">
    <AppHeader />

    <div v-if="!loading && !error && title">
      <!-- Hero Section -->
      <section class="bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 py-16 text-center">
        <h1 class="font-display text-4xl font-bold text-white">{{ title.name }} Collection</h1>
        <p class="mt-4 text-lg text-primary-100">
          Browse all {{ cards.length }} cards in this title
        </p>
      </section>

      <!-- Navigation -->
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        <router-link
          :to="{ name: 'Title', params: { slug: title.slug } }"
          class="inline-flex items-center text-primary-600 hover:text-primary-700 transition-colors"
        >
          <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
          </svg>
          Back to {{ title.name }}
        </router-link>
      </div>

      <!-- Cards Sections -->
      <main class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-16 space-y-12">
        <div v-if="cardsLoading" class="text-center py-12">
          <p class="text-gray-600 dark:text-gray-400">Loading cards...</p>
        </div>

        <div v-else-if="cards.length === 0" class="text-center py-12">
          <p class="text-gray-600 dark:text-gray-400">No cards found for this title.</p>
        </div>

        <div v-else>
          <!-- Common Cards Section -->
          <section v-if="commonCards.length > 0">
            <h2 class="font-display text-2xl font-bold text-gray-900 dark:text-white mb-6">
              Common Cards
            </h2>
            <div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3">
              <CollectionCard
                v-for="card in commonCards"
                :key="card.slug"
                :card="card"
              />
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
            <div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3">
              <CollectionCard
                v-for="card in factionCards"
                :key="card.slug"
                :card="card"
              />
            </div>
          </section>
        </div>
      </main>
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
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import axios from '../config/api.js'
import AppHeader from '../components/AppHeader.vue'
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
}

const route = useRoute()
const title = ref<TitleData | null>(null)
const cards = ref<Card[]>([])
const loading = ref<boolean>(true)
const cardsLoading = ref<boolean>(false)
const error = ref<string | null>(null)

// Computed properties for organizing cards by faction
const commonCards = computed(() => {
  return cards.value.filter(card => !card.faction)
})

const factionCardGroups = computed(() => {
  const factionGroups = new Map<string, Card[]>()

  cards.value.forEach(card => {
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

onMounted(async () => {
  await fetchTitle()
  if (title.value) {
    await fetchCards()
  }
})
</script>

<style scoped>
.title-cards-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
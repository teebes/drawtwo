<template>
  <div class="deck-detail-page">
    <AppHeader />

    <div v-if="!loading && !error && deck">
      <section class="bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 py-16 text-center">
        <h1 class="font-display text-4xl font-bold">{{ deck.name }}</h1>
        <p class="mt-4 text-lg text-gray-200" v-if="deck.description">{{ deck.description }}</p>
        <div class="mt-4 flex items-center justify-center space-x-6 text-sm text-gray-200">
          <span>{{ deck.hero.name }}</span>
          <span>•</span>
          <span>{{ deck.total_cards }} cards</span>
        </div>
      </section>

      <main class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-8 mt-8">
        <Panel title="Deck Statistics">
          <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div class="text-center">
              <div class="text-2xl font-bold text-primary-600">{{ deck.total_cards }}</div>
              <div class="text-sm text-gray-600">Total Cards</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-primary-600">{{ deck.cards.length }}</div>
              <div class="text-sm text-gray-600">Unique Cards</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-primary-600">{{ deck.hero.health }}</div>
              <div class="text-sm text-gray-600">Hero Health</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-primary-600">{{ averageCost.toFixed(1) }}</div>
              <div class="text-sm text-gray-600">Avg. Cost</div>
            </div>
          </div>
        </Panel>

        <Panel title="Cards" v-if="deck.cards.length > 0">
          <div class="space-y-2">
            <div
              v-for="card in deck.cards"
              :key="card.id"
              class="flex items-center justify-between rounded-lg bg-gray-50 p-3 dark:bg-gray-800"
            >
              <div class="flex items-center space-x-3">
                <div class="flex h-8 w-8 items-center justify-center rounded bg-primary-100 text-sm font-bold text-primary-600">
                  {{ card.cost }}
                </div>
                <div>
                  <div class="font-medium">{{ card.name }}</div>
                  <div class="text-sm text-gray-600">
                    {{ card.card_type }}
                    <span v-if="card.attack !== null && card.health !== null">
                      • {{ card.attack }}/{{ card.health }}
                    </span>
                  </div>
                </div>
              </div>
              <div class="text-lg font-bold text-gray-900">{{ card.count }}x</div>
            </div>
          </div>
        </Panel>

        <Panel title="Empty Deck" v-else>
          <div class="text-center py-8">
            <p class="text-gray-600 mb-4">This deck doesn't have any cards yet.</p>
            <button class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
              Add Cards
            </button>
          </div>
        </Panel>
      </main>
    </div>

    <div class="text-center p-8" v-if="error">
      <h1 class="text-2xl font-bold text-red-600 mb-4">Error</h1>
      <p class="text-gray-600">{{ error }}</p>
    </div>

    <div class="text-center p-8" v-if="loading">
      <p class="text-gray-600">Loading deck...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import axios from '../config/api.js'
import AppHeader from '../components/AppHeader.vue'
import Panel from '../components/layout/Panel.vue'

interface DeckCard {
  id: number
  name: string
  slug: string
  cost: number
  card_type: string
  attack: number | null
  health: number | null
  count: number
}

interface DeckData {
  id: number
  name: string
  description: string
  hero: {
    id: number
    name: string
    slug: string
    health: number
  }
  cards: DeckCard[]
  total_cards: number
  created_at: string
  updated_at: string
}

const route = useRoute()
const deck = ref<DeckData | null>(null)
const loading = ref<boolean>(true)
const error = ref<string | null>(null)

const averageCost = computed(() => {
  if (!deck.value || deck.value.cards.length === 0) return 0

  const totalCost = deck.value.cards.reduce((sum, card) => sum + (card.cost * card.count), 0)
  return totalCost / deck.value.total_cards
})

const fetchDeck = async (): Promise<void> => {
  try {
    const deckId = route.params.id as string

    // Handle "new" deck creation (placeholder for now)
    if (deckId === 'new') {
      // For now, just show a placeholder
      deck.value = {
        id: 0,
        name: 'New Deck',
        description: 'Create a new deck for this title',
        hero: {
          id: 0,
          name: 'Select Hero',
          slug: '',
          health: 0
        },
        cards: [],
        total_cards: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
      loading.value = false
      return
    }

    const response = await axios.get(`/collection/decks/${deckId}/`)
    deck.value = response.data
  } catch (err) {
    if (err.response?.status === 404) {
      error.value = 'Deck not found'
    } else {
      error.value = err.response?.data?.message || err.message || 'Failed to load deck'
    }
    console.error('Error fetching deck:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDeck()
})
</script>

<style scoped>
.deck-detail-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
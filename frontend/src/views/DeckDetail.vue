<template>
  <div class="deck-detail-page">

    <div v-if="!loading && !error && deck">
      <section class="relative bg-gray-300 overflow-hidden h-24 flex items-center justify-center space-x-6">
        <img
          v-if="deck.hero.art_url && !heroImageError"
          :src="deck.hero.art_url"
          :alt="`${deck.hero.name} artwork`"
          class="inset-0 h-full object-contain object-center border-gray-600 border-2 rounded-lg"
          @error="onHeroImageError"
        />

        <div class="">
          <h1 class="font-display text-4xl font-bold dark:text-gray-900">{{ deck.name }}</h1>
        </div>
      </section>

      <main class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-8 mt-8">
        <Panel>
          <div class="grid gap-4 grid-cols-4 sm:grid-cols-4">
            <div class="text-center">
              <div class="text-2xl font-bold text-primary-600">{{ deck.total_cards }}</div>
              <div class="text-xs text-gray-600">Total Cards</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-primary-600">{{ deck.cards.length }}</div>
              <div class="text-xs text-gray-600">Unique Cards</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-primary-600">{{ deck.hero.health }}</div>
              <div class="text-xs text-gray-600">Hero Health</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-primary-600">{{ averageCost.toFixed(1) }}</div>
              <div class="text-xs text-gray-600">Avg. Cost</div>
            </div>
          </div>
        </Panel>

        <Panel v-if="deck.cards.length > 0">
          <div class="space-y-2">
            <div
              v-for="card in sortedCards"
              :key="card.id"
              class="flex items-center rounded-lg bg-gray-50 dark:bg-gray-800 space-x-2"
            >
              <!-- Card cost badge -->
              <div class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded bg-gray-200 text-sm font-semibold text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                {{ card.cost }}
              </div>

              <!-- Clickable count -->
              <div class="relative flex-shrink-0">
                <input
                  v-if="editingCardId === card.id"
                  v-model="editingCount"
                  @blur="saveCountEdit(card)"
                  @keyup.enter="saveCountEdit(card)"
                  @keyup.esc="cancelCountEdit"
                  type="text"
                  class="w-10 rounded border border-primary-500 bg-white px-2 py-1 text-center text-sm font-bold dark:bg-gray-900 dark:text-gray-100"
                  ref="countInput"
                />
                <button
                  v-else
                  @click="startCountEdit(card)"
                  class="w-10 rounded px-2 py-1 text-center text-sm font-bold text-gray-700 hover:bg-gray-200 dark:text-gray-200 dark:hover:bg-gray-700 transition-colors"
                  title="Click to edit count"
                >
                  {{ card.count }}x
                </button>
              </div>

              <!-- Up/Down triangle buttons stacked vertically -->
              <div class="flex flex-col flex-shrink-0">
                <button
                  @click="incrementCard(card)"
                  class="flex h-5 w-8 items-center justify-center rounded-t bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 transition-colors"
                  title="Increase count"
                >
                  <span class="text-sm leading-none">▲</span>
                </button>
                <button
                  @click="decrementCard(card)"
                  class="flex h-5 w-8 items-center justify-center rounded-b bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 transition-colors"
                  title="Decrease count"
                >
                  <span class="text-sm leading-none">▼</span>
                </button>
              </div>

              <!-- Card name and info -->
              <div class="card-info flex-1 flex flex-row items-center min-w-0">
                <div class="font-medium truncate">{{ card.name }}</div>
                <div class="text-sm text-gray-600 dark:text-gray-400 ml-4 flex-shrink-0">
                  <span v-if="card.card_type === 'creature'">
                    {{ card.attack }}/{{ card.health }}
                  </span>
                  <span v-else>Spell</span>
                </div>
              </div>

              <!-- Delete button -->
              <button
                @click="deleteCard(card)"
                class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-300 transition-colors"
                title="Remove card"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        </Panel>

        <Panel>
          <div class="grid grid-cols-3 space-x-2">
            <GameButton variant="danger" @click="deleteDeck">Delete Deck</GameButton>
            <router-link :to="{ name: 'DeckEdit', params: { slug: deck.title.slug, id: deck.id } }">
              <GameButton variant="secondary" class="w-full">Edit Deck</GameButton>
            </router-link>
            <GameButton variant="primary" @click="openCardModal">Add Card</GameButton>
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

    <!-- Card Selection Modal -->
    <CardSelectionModal
      :is-open="showCardModal"
      :title-slug="titleSlug"
      @close="closeCardModal"
      @card-selected="onCardSelected"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../config/api'
import Panel from '../components/layout/Panel.vue'
import CardSelectionModal from '../components/ui/CardSelectionModal.vue'
import type { DeckCard, Card } from '../types/card'
import GameButton from '../components/ui/GameButton.vue'
import { useNotificationStore } from '../stores/notifications'

interface DeckData {
  id: number
  name: string
  description: string
  title: {
    id: number
    slug: string
    name: string
  }
  hero: {
    id: number
    name: string
    slug: string
    health: number
    art_url?: string | null
  }
  cards: DeckCard[]
  total_cards: number
  created_at: string
  updated_at: string
}

const route = useRoute()
const router = useRouter()
const notificationStore = useNotificationStore()
const deck = ref<DeckData | null>(null)
const loading = ref<boolean>(true)
const error = ref<string | null>(null)

// Inline count editing state
const editingCardId = ref<number | null>(null)
const editingCount = ref<string>('1')
const countInput = ref<HTMLInputElement | null>(null)

// Hero image error handling
const heroImageError = ref(false)

// Modal state
const showCardModal = ref<boolean>(false)

// Computed property to get title slug from deck
const titleSlug = computed(() => {
  return deck.value?.title?.slug || ''
})

const averageCost = computed(() => {
  if (!deck.value || deck.value.cards.length === 0) return 0

  const totalCost = deck.value.cards.reduce((sum, card) => sum + (card.cost * card.count), 0)
  return totalCost / deck.value.total_cards
})

const sortedCards = computed(() => {
  if (!deck.value || !deck.value.cards) return []

  return [...deck.value.cards].sort((a, b) => {
    // Sort by cost first
    if (a.cost !== b.cost) {
      return a.cost - b.cost
    }
    // Then by name alphabetically
    return a.name.localeCompare(b.name)
  })
})

const onHeroImageError = (): void => {
  heroImageError.value = true
}

const openCardModal = (): void => {
  showCardModal.value = true
}

const closeCardModal = (): void => {
  showCardModal.value = false
}

const onCardSelected = async (card: Card): Promise<void> => {
  if (!deck.value) return

  try {
    const response = await axios.post(`/collection/decks/${deck.value.id}/cards/add/`, {
      // card_id: card.id,
      card_slug: card.slug,
      count: 1
    })

    // Check if card already exists in deck
    const existingCardIndex = deck.value.cards.findIndex(c => c.id === card.id)

    if (existingCardIndex !== -1) {
      // Update existing card count
      deck.value.cards[existingCardIndex].count = response.data.count
    } else {
      // Add new card to deck
      const newDeckCard: DeckCard = {
        ...card,
        count: response.data.count
      }
      deck.value.cards.push(newDeckCard)
    }

    // Recalculate total cards
    deck.value.total_cards = deck.value.cards.reduce((sum, card) => sum + card.count, 0)

    // Show success notification
    notificationStore.handleApiSuccess(response)
    closeCardModal()
  } catch (err: any) {
    console.error('Error adding card to deck:', err)
    notificationStore.handleApiError(err)
  }
}

const updateCardCount = async (card: DeckCard, newCount: number): Promise<void> => {
  if (!deck.value || newCount < 1 || newCount > 10) return

  try {
    const response = await axios.put(`/collection/decks/${deck.value.id}/cards/${card.id}/`, {
      count: newCount
    })

    // Update local state
    const cardIndex = deck.value.cards.findIndex(c => c.id === card.id)
    if (cardIndex !== -1) {
      deck.value.cards[cardIndex].count = newCount
      // Recalculate total cards
      deck.value.total_cards = deck.value.cards.reduce((sum, card) => sum + card.count, 0)
    }

    notificationStore.handleApiSuccess(response)
  } catch (err: any) {
    console.error('Error updating card count:', err)
    notificationStore.handleApiError(err)
  }
}

const incrementCard = async (card: DeckCard): Promise<void> => {
  const newCount = Math.min(card.count + 1, 10)
  if (newCount !== card.count) {
    await updateCardCount(card, newCount)
  }
}

const decrementCard = async (card: DeckCard): Promise<void> => {
  if (card.count > 1) {
    await updateCardCount(card, card.count - 1)
  }
}

const startCountEdit = (card: DeckCard): void => {
  editingCardId.value = card.id
  editingCount.value = card.count.toString()

  // Focus the input on next tick
  setTimeout(() => {
    const input = document.querySelector('input[type="text"]') as HTMLInputElement
    if (input) {
      input.focus()
      input.select()
    }
  }, 0)
}

const cancelCountEdit = (): void => {
  editingCardId.value = null
  editingCount.value = '1'
}

const saveCountEdit = async (card: DeckCard): Promise<void> => {
  const newCount = parseInt(editingCount.value, 10)

  // Validate the input
  if (isNaN(newCount) || newCount < 1 || newCount > 10) {
    // Invalid input, just cancel
    cancelCountEdit()
    return
  }

  if (newCount === card.count) {
    // No change, just cancel
    cancelCountEdit()
    return
  }

  await updateCardCount(card, newCount)
  cancelCountEdit()
}

const deleteCard = async (card: DeckCard): Promise<void> => {
  if (!deck.value) return

  // Show confirmation dialog
  const confirmed = window.confirm(
    `Remove ${card.name} from deck?`
  )

  if (!confirmed) return

  try {
    await axios.delete(`/collection/decks/${deck.value.id}/cards/${card.id}/delete/`)

    // Update local state
    deck.value.cards = deck.value.cards.filter(c => c.id !== card.id)
    deck.value.total_cards = deck.value.cards.reduce((sum, card) => sum + card.count, 0)

    notificationStore.success('Card removed from deck successfully')
  } catch (err: any) {
    console.error('Error deleting card:', err)
    notificationStore.handleApiError(err)
  }
}

const deleteDeck = async (): Promise<void> => {
  if (!deck.value) return

  // Show confirmation dialog
  const confirmed = window.confirm(
    `Are you sure you want to delete the deck "${deck.value.name}"? This action cannot be undone.`
  )

  if (!confirmed) return

  try {
    const response = await axios.delete(`/collection/decks/${deck.value.id}/`)

    // Show success notification
    notificationStore.handleApiSuccess(response)

    // Navigate back to title page
    router.push({
      name: 'Title',
      params: { slug: deck.value.title.slug }
    })
  } catch (err: any) {
    console.error('Error deleting deck:', err)
    notificationStore.handleApiError(err)
  }
}

const fetchDeck = async (): Promise<void> => {
  try {
    const deckId = route.params.id as string
    const response = await axios.get(`/collection/decks/${deckId}/`)
    deck.value = response.data
  } catch (err: any) {
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

  // Temporary test notifications for styling. Uncomment to test.
  /*
  notificationStore.success('This is a test success message!')
  notificationStore.error('This is a test error message!')
  notificationStore.warning('This is a test warning message!')
  notificationStore.info('This is a test info message!')
  */
})
</script>

<style scoped>
.deck-detail-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
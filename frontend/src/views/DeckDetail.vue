<template>
  <div class="deck-detail-page">

    <div v-if="!loading && !error && deck">
      <section class="page-banner">
        <h1 class="font-display text-4xl font-bold">{{ deck.name }}</h1>
        <p class="mt-4 text-lg text-gray-200" v-if="deck.description">{{ deck.description }}</p>
        <div class="mt-4 flex items-center justify-center space-x-6 text-sm text-gray-200">
          <span>{{ deck.hero.name }}</span>
          <span>•</span>
          <span>{{ deck.total_cards }} cards</span>
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
          <div class="">
            <div
              v-for="card in deck.cards"
              :key="card.id"
              class="flex items-center justify-between rounded-lg bg-gray-50 p-1 dark:bg-gray-800"
            >
              <div class="flex items-center space-x-3 w-full">

                <!-- Edit mode -->
                <template v-if="editingCardId === card.id">

                  <!--
                    Because we want to display the actions below the card summary
                    on low widths, we make two rows. On wider displays the second
                    row is always empty.
                   -->
                  <div class="flex flex-col w-full">

                    <!-- First Row -->
                    <div class="flex flex-row w-full">

                      <!-- Editable count -->
                      <div class="flex items-center space-x-2">
                        <input
                          v-model.number="editingCount"
                          type="number"
                          min="1"
                          max="10"
                          class="input-field">
                        <span class="text-sm text-gray-500">x</span>
                      </div>

                      <!-- Card cost, name and info -->
                      <div
                        class="flex h-8 items-center justify-center rounded bg-primary-100 text-sm font-bold text-primary-600 w-8 ml-3 mr-3"
                      >
                        {{ card.cost }}
                      </div>

                      <div class="card-info flex-1 flex flex-row items-center w-full">
                        <div class="font-medium">{{ card.name }}</div>
                        <div class="text-sm text-gray-600 ml-4">
                          <span v-if="card.card_type === 'minion'">
                            {{ card.attack }}/{{ card.health }}
                          </span>
                          <span v-else>Spell</span>
                        </div>
                      </div>

                      <!-- Edit actions on wide displays -->
                      <div class="flex space-x-2 hidden sm:flex">
                        <GameButton variant="primary" @click="saveEdit">Save</GameButton>
                        <GameButton variant="secondary" @click="cancelEdit">Cancel</GameButton>
                        <GameButton variant="danger" @click="deleteCard(card.id)">Delete</GameButton>
                      </div>
                    </div>

                    <!-- Second row, edit actions on narrow displays -->
                    <div class="flex space-x-2 sm:hidden w-full mt-2 mb-4">
                      <GameButton variant="primary" @click="saveEdit">Save</GameButton>
                      <GameButton variant="secondary" @click="cancelEdit">Cancel</GameButton>
                      <GameButton variant="danger" @click="deleteCard(card.id)">Delete</GameButton>
                    </div>
                </div>
                </template>

                <!-- Normal mode -->
                <template v-else>
                  <div class="text-lg font-bold text-gray-500 w-8">{{ card.count }}x</div>

                  <div class="flex h-8 w-8 items-center justify-center rounded bg-primary-100 text-sm font-bold text-primary-600">
                    {{ card.cost }}
                  </div>

                  <div class="card-info flex-1 flex flex-row items-center w-full">
                    <div class="font-medium">{{ card.name }}</div>
                    <div class="text-sm text-gray-600 ml-4">
                      <span v-if="card.card_type === 'minion'">
                        {{ card.attack }}/{{ card.health }}
                      </span>
                                              <span v-else>Spell</span>
                    </div>
                  </div>

                  <div class="">
                    <GameButton variant="secondary" @click="startEdit(card)">Edit</GameButton>
                  </div>
                </template>

              </div>
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
import axios from '../config/api.js'
import Panel from '../components/layout/Panel.vue'
import CardSelectionModal from '../components/ui/CardSelectionModal.vue'
import type { DeckCard, Card } from '../types/card'
import GameButton from '../components/ui/GameButton.vue'
import { useNotificationStore } from '../stores/notifications.js'

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

const editingCardId = ref<number | null>(null)
const editingCount = ref<number>(1)

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
      card_id: card.id,
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
  } catch (err) {
    console.error('Error adding card to deck:', err)
    notificationStore.handleApiError(err)
  }
}

const startEdit = (card: DeckCard): void => {
  console.log('starting to edit card')
  console.log(card)
  console.log(editingCount.value)

  editingCardId.value = card.id
  editingCount.value = card.count
}

const cancelEdit = (): void => {
  editingCardId.value = null
  editingCount.value = 1
}

const saveEdit = async (): Promise<void> => {
  if (!editingCardId.value || !deck.value) return

  try {
    const response = await axios.put(`/collection/decks/${deck.value.id}/cards/${editingCardId.value}/`, {
      count: editingCount.value
    })

    // Update local state
    const cardIndex = deck.value.cards.findIndex(c => c.id === editingCardId.value)
    if (cardIndex !== -1) {
      deck.value.cards[cardIndex].count = editingCount.value
      // Recalculate total cards
      deck.value.total_cards = deck.value.cards.reduce((sum, card) => sum + card.count, 0)
    }

    notificationStore.handleApiSuccess(response)
    cancelEdit()
  } catch (err) {
    console.error('Error saving card count:', err)
    notificationStore.handleApiError(err)
  }
}

const deleteCard = async (cardId: number): Promise<void> => {
  if (!deck.value) return

  try {
    await axios.delete(`/collection/decks/${deck.value.id}/cards/${cardId}/delete/`)

    // Update local state
    deck.value.cards = deck.value.cards.filter(c => c.id !== cardId)
    deck.value.total_cards = deck.value.cards.reduce((sum, card) => sum + card.count, 0)

    notificationStore.success('Card removed from deck successfully')
    cancelEdit()
  } catch (err) {
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
  } catch (err) {
    console.error('Error deleting deck:', err)
    notificationStore.handleApiError(err)
  }
}

const fetchDeck = async (): Promise<void> => {
  try {
    const deckId = route.params.id as string
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
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
              <div class="text-2xl font-bold text-500">{{ deck.total_cards }}</div>
              <div class="text-xs text-gray-500">Total Cards</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-500">{{ deck.cards.length }}</div>
              <div class="text-xs text-gray-500">Unique Cards</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-500">{{ deck.hero.health }}</div>
              <div class="text-xs text-gray-500">Hero Health</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-500">{{ averageCost.toFixed(1) }}</div>
              <div class="text-xs text-gray-500">Avg. Cost</div>
            </div>
          </div>

          <div v-if="powerCurve.length > 0" class="mt-4 border-t border-gray-200 pt-4 dark:border-gray-700">
            <div class="mb-2 flex items-center justify-between">
              <h2 class="text-xs font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300">Power Curve</h2>
              <span class="text-[11px] text-gray-500 dark:text-gray-400">Cards by energy cost</span>
            </div>

            <div class="flex items-end gap-1 overflow-x-auto pb-1">
              <div
                v-for="bucket in powerCurve"
                :key="bucket.cost"
                class="flex min-w-[28px] flex-col items-center"
              >
                <span class="mb-1 text-[10px] font-semibold text-gray-500 dark:text-gray-400">{{ bucket.count }}</span>
                <div
                  class="w-5 rounded-t bg-secondary-500 transition-all duration-300"
                  :class="bucket.count === 0 ? 'opacity-20' : 'opacity-90'"
                  :style="{ height: `${bucket.height}px` }"
                />
                <span class="mt-1 text-[10px] font-semibold text-gray-600 dark:text-gray-300">{{ bucket.cost }}</span>
              </div>
            </div>
          </div>
        </Panel>

        <transition name="panel-fade" mode="out-in">
          <Panel v-if="displayCards.length > 0" :key="isAddCardMode ? 'add-mode' : 'normal-mode'">
            <transition-group
              name="card-list"
              tag="div"
              class="space-y-2"
            >
            <div
              v-for="card in displayCards"
              :key="card.id"
              class="card-item flex items-center rounded-lg bg-gray-50 dark:bg-gray-800 space-x-2"
            >
              <!-- Card cost badge -->
              <div class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-secondary-500 text-sm font-semibold text-gray-700 dark:text-gray-300">
                {{ card.cost }}
              </div>

              <!-- For cards in deck: show count and up/down controls -->
              <template v-if="isCardInDeck(card)">
                <!-- Clickable count -->
                <div class="relative flex-shrink-0">
                  <input
                    v-if="editingCardId === card.id"
                    v-model="editingCount"
                    @blur="saveCountEdit(card as DeckCard)"
                    @keyup.enter="saveCountEdit(card as DeckCard)"
                    @keyup.esc="cancelCountEdit"
                    type="text"
                    class="w-10 rounded border border-primary-500 bg-white px-2 py-1 text-center text-sm font-bold dark:bg-gray-900 dark:text-gray-100"
                    ref="countInput"
                  />
                  <button
                    v-else
                    @click="startCountEdit(card as DeckCard)"
                    class="w-10 rounded px-2 py-1 text-center text-sm font-bold text-gray-700 hover:bg-gray-200 dark:text-gray-200 dark:hover:bg-gray-700 transition-colors"
                    title="Click to edit count"
                  >
                    {{ (card as DeckCard).count }}x
                  </button>
                </div>

                <!-- Up/Down triangle buttons stacked vertically -->
                <div class="flex flex-col flex-shrink-0">
                  <button
                    @click="incrementCard(card as DeckCard)"
                    class="flex h-4 w-8 items-center justify-center rounded-t bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 transition-colors"
                    title="Increase count"
                  >
                    <span class="text-sm leading-none">▲</span>
                  </button>
                  <button
                    @click="decrementCard(card as DeckCard)"
                    class="flex h-4 w-8 items-center justify-center rounded-b bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 transition-colors"
                    title="Decrease count"
                  >
                    <span class="text-sm leading-none">▼</span>
                  </button>
                </div>
              </template>

              <!-- For cards not in deck: show Add Card button -->
              <template v-else>
                <GameButton
                  variant="primary"
                  @click="addCardToDeck(card)"
                  class="flex-shrink-0"
                >
                  Add Card
                </GameButton>
              </template>

              <!-- Card name and info -->
              <div class="card-info flex-1 flex flex-row items-center min-w-0">
                <div class="font-medium truncate ml-4">
                  <!-- {{ card.name }} -->
                  <button
                    @click="openCardModal(card)"
                    class="text-left hover:text-blue-600 hover:underline focus:outline-none"
                  >
                    {{ card.name }}
                  </button>
                </div>
                <div class="text-sm text-gray-600 dark:text-gray-400 ml-4 flex-shrink-0">
                  <span v-if="card.card_type === 'creature'">
                    {{ card.attack }}/{{ card.health }}
                  </span>
                  <span v-else>Spell</span>
                </div>
              </div>

              <!-- Delete button (only for cards in deck) -->
              <button
                v-if="isCardInDeck(card)"
                @click="deleteCard(card as DeckCard)"
                class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-300 transition-colors"
                title="Remove card"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>
          </transition-group>
          </Panel>
        </transition>

        <Panel>
          <div class="grid grid-cols-3 space-x-2">
            <GameButton variant="danger" @click="deleteDeck">Delete Deck</GameButton>
            <router-link :to="{ name: 'DeckEdit', params: { slug: deck.title.slug, id: deck.id } }">
              <GameButton variant="secondary" class="w-full">Edit Deck</GameButton>
            </router-link>
            <GameButton
              :variant="isAddCardMode ? 'secondary' : 'primary'"
              @click="toggleAddCardMode"
            >
              {{ isAddCardMode ? 'Cancel Edit Cards' : 'Edit Cards' }}
            </GameButton>
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

    <!-- Card Detail Modal -->
    <BaseModal :show="showCardModal" @close="closeCardModal">
      <CardDetailContent
        v-if="selectedCard"
        :card="selectedCard"
        :title-slug="titleSlug"
        :can-edit="false"
      />
    </BaseModal>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../config/api'
import Panel from '../components/layout/Panel.vue'
import type { DeckCard, Card } from '../types/card'
import GameButton from '../components/ui/GameButton.vue'
import { useNotificationStore } from '../stores/notifications'
import BaseModal from '../components/modals/BaseModal.vue'
import CardDetailContent from '../components/game/CardDetailContent.vue'

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
  all_cards?: Card[]  // All available collectible cards for adding to deck
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

// Add Card mode state
const isAddCardMode = ref<boolean>(false)
const allCards = ref<Card[]>([])
const allCardsLoading = ref<boolean>(false)
const allCardsError = ref<string | null>(null)

const selectedCard = ref<Card | null>(null)
const showCardModal = ref(false)

const openCardModal = (card: Card) => {
  console.log('openCardModal', card)
  selectedCard.value = card
  showCardModal.value = true
}

const closeCardModal = () => {
  showCardModal.value = false
  // Optional: clear selected card after animation
  setTimeout(() => {
    selectedCard.value = null
  }, 300)
}

// Computed property to get title slug from deck
const titleSlug = computed(() => {
  return deck.value?.title?.slug || ''
})

const averageCost = computed(() => {
  if (!deck.value || deck.value.cards.length === 0) return 0

  const totalCost = deck.value.cards.reduce((sum, card) => sum + (card.cost * card.count), 0)
  return totalCost / deck.value.total_cards
})

type PowerCurveBucket = {
  cost: number
  count: number
  height: number
}

const powerCurve = computed<PowerCurveBucket[]>(() => {
  if (!deck.value || deck.value.cards.length === 0) return []

  const costCounts = new Map<number, number>()

  deck.value.cards.forEach(card => {
    const normalizedCost = Number.isFinite(card.cost) ? Math.max(0, Math.round(card.cost)) : 0
    costCounts.set(normalizedCost, (costCounts.get(normalizedCost) || 0) + card.count)
  })

  const costs = Array.from(costCounts.keys())
  const counts = Array.from(costCounts.values())
  const maxCost = costs.length > 0 ? Math.max(...costs) : 0
  const maxCount = counts.length > 0 ? Math.max(...counts) : 1

  if (maxCost < 1) return []

  return Array.from({ length: maxCost }, (_, index) => {
    const cost = index + 1
    const count = costCounts.get(cost) || 0
    const height = count > 0
      ? Math.max(8, Math.round((count / maxCount) * 36) + 4)
      : 8

    return {
      cost,
      count,
      height
    }
  })
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

// Create a map of deck cards by card id for quick lookup
const deckCardsMap = computed(() => {
  if (!deck.value || !deck.value.cards) return new Map<number, DeckCard>()

  const map = new Map<number, DeckCard>()
  deck.value.cards.forEach(card => {
    map.set(card.id, card)
  })
  return map
})

// Display cards: when in Add Card mode, show all cards; otherwise show only deck cards
const displayCards = computed(() => {
  if (isAddCardMode.value) {
    // Merge all cards with deck cards
    // For cards in deck, use the deck card data (with count)
    // For cards not in deck, use the card data
    return allCards.value.map(card => {
      const deckCard = deckCardsMap.value.get(card.id)
      return deckCard || card
    }).sort((a, b) => {
      // Sort by cost first
      if (a.cost !== b.cost) {
        return a.cost - b.cost
      }
      // Then by name alphabetically
      return a.name.localeCompare(b.name)
    })
  } else {
    // Normal mode: show only deck cards
    return sortedCards.value
  }
})

// Helper function to check if a card is in the deck
const isCardInDeck = (card: Card | DeckCard): boolean => {
  return deckCardsMap.value.has(card.id)
}

const onHeroImageError = (): void => {
  heroImageError.value = true
}

const toggleAddCardMode = (): void => {
  isAddCardMode.value = !isAddCardMode.value
  // Use all_cards from deck response if available, otherwise fetch
  if (isAddCardMode.value && allCards.value.length === 0) {
    if (deck.value?.all_cards) {
      allCards.value = deck.value.all_cards
    } else {
      fetchAllCards()
    }
  }
}

const fetchAllCards = async (): Promise<void> => {
  if (!titleSlug.value) return

  try {
    allCardsLoading.value = true
    allCardsError.value = null
    const response = await axios.get(`/titles/${titleSlug.value}/cards/`)
    allCards.value = response.data || []
  } catch (err: any) {
    console.error('Error fetching all cards:', err)
    allCardsError.value = err.response?.data?.message || err.message || 'Failed to load cards'
    notificationStore.handleApiError(err)
  } finally {
    allCardsLoading.value = false
  }
}

const addCardToDeck = async (card: Card): Promise<void> => {
  if (!deck.value) return

  try {
    const response = await axios.post(`/collection/decks/${deck.value.id}/cards/add/`, {
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
  } else {
    await deleteCard(card)
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
    // Initialize allCards from deck response if available
    if (deck.value?.all_cards) {
      allCards.value = deck.value.all_cards
    }
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
  display: flex;
  flex-direction: column;
}

/* Panel fade transition for mode switching */
.panel-fade-enter-active,
.panel-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.panel-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.panel-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Card list transition animations */
.card-list-enter-active,
.card-list-leave-active {
  transition: all 0.3s ease;
}

.card-list-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.card-list-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.card-list-move {
  transition: transform 0.3s ease;
}

/* Ensure smooth transitions for card item content */
.card-item {
  transition: background-color 0.2s ease;
}
</style>

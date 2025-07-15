<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 overflow-y-auto" @click="closeModal">
    <div class="flex min-h-screen items-center justify-center p-4">
      <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"></div>

      <div
        class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden"
        @click.stop
      >
        <!-- Header -->
        <div class="border-b border-gray-200 dark:border-gray-700 px-6 py-4">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
              Add Card to Deck
            </h2>
            <button
              @click="closeModal"
              class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="p-8 text-center">
          <p class="text-gray-600 dark:text-gray-400">Loading cards...</p>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="p-8 text-center">
          <p class="text-red-600 dark:text-red-400">{{ error }}</p>
        </div>

        <!-- Cards Grid -->
        <div v-else class="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          <div v-if="cards.length === 0" class="text-center py-12">
            <p class="text-gray-600 dark:text-gray-400">No cards found for this title.</p>
          </div>

          <div v-else>
            <!-- Common Cards Section -->
            <section v-if="commonCards.length > 0" class="mb-8">
              <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Common Cards
              </h3>
              <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                <div
                  v-for="card in commonCards"
                  :key="card.slug"
                  class="cursor-pointer transition-transform hover:scale-105"
                  @click="selectCard(card)"
                >
                  <CollectionCard
                    :card="card"
                    heightMode="fixed"
                    height="sm"/>
                </div>
              </div>
            </section>

            <!-- Faction Cards Sections -->
            <section
              v-for="[factionName, factionCards] in factionCardGroups"
              :key="factionName"
              class="mb-8"
            >
              <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 capitalize">
                {{ factionName }} Cards
              </h3>
              <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                <div
                  v-for="card in factionCards"
                  :key="card.slug"
                  class="cursor-pointer transition-transform hover:scale-105"
                  @click="selectCard(card)"
                >
                  <CollectionCard
                    :card="card"
                    heightMode="fixed"
                    height="sm"/>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import axios from '../../config/api.js'
import CollectionCard from '../game/CollectionCard.vue'
import type { Card } from '../../types/card'

interface Props {
  isOpen: boolean
  titleSlug: string
  lockScroll?: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'card-selected', card: Card): void
}

const props = withDefaults(defineProps<Props>(), {
  lockScroll: true
})
const emit = defineEmits<Emits>()

const cards = ref<Card[]>([])
const loading = ref<boolean>(false)
const error = ref<string | null>(null)

// Store original body overflow to restore later
let originalBodyOverflow = ''

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

const lockBodyScroll = (): void => {
  if (props.lockScroll && typeof document !== 'undefined') {
    originalBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  }
}

const unlockBodyScroll = (): void => {
  if (props.lockScroll && typeof document !== 'undefined') {
    document.body.style.overflow = originalBodyOverflow
  }
}

const closeModal = (): void => {
  unlockBodyScroll()
  emit('close')
}

const selectCard = (card: Card): void => {
  emit('card-selected', card)
  closeModal()
}

const fetchCards = async (): Promise<void> => {

  if (!props.titleSlug) return


  try {
    loading.value = true
    error.value = null
    const response = await axios.get(`/titles/${props.titleSlug}/cards/`)
    cards.value = response.data || []
  } catch (err) {
    console.error('Error fetching cards:', err)
    error.value = err.response?.data?.message || err.message || 'Failed to load cards'
  } finally {
    loading.value = false
  }
}

// Watch for modal opening/closing to manage scroll lock
watch(() => props.isOpen, (newValue) => {
  if (newValue) {
    if (props.lockScroll) {
      lockBodyScroll()
    }
    fetchCards()
  } else {
    if (props.lockScroll) {
      unlockBodyScroll()
    }
  }
})

// Ensure scroll is unlocked when component is unmounted
onUnmounted(() => {
  if (props.lockScroll) {
    unlockBodyScroll()
  }
})
</script>

<style scoped>
/* Additional styles if needed */
</style>
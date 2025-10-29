<template>
  <div class="deck-edit-page">
    <section class="page-banner">
      <h1 class="font-display text-4xl font-bold">
        {{ isEditMode ? 'Edit Deck' : 'Create New Deck' }}
      </h1>
      <p class="mt-4 text-lg text-gray-200" v-if="titleData">
        for {{ titleData.name }}
      </p>
    </section>

    <main class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-8 mt-8">
      <Panel>
        <form @submit.prevent="saveDeck" class="space-y-6">
          <!-- Deck Name -->
          <div>
            <label for="deck-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Deck Name
            </label>
            <input
              id="deck-name"
              v-model="deckName"
              type="text"
              required
              class="input-field w-full"
              placeholder="Enter deck name"
              :disabled="saving"
            />
          </div>

          <!-- Hero Selection -->
          <div>
            <label for="hero-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Hero
            </label>
            <select
              id="hero-select"
              v-model="selectedHeroId"
              required
              class="input-field w-full"
              :disabled="saving || heroesLoading"
            >
              <option value="">Select a hero</option>
              <option
                v-for="hero in heroes"
                :key="hero.id"
                :value="hero.id"
              >
                {{ hero.name }}
              </option>
            </select>
          </div>

          <!-- Deck Description -->
          <div>
            <label for="deck-description" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Description (optional)
            </label>
            <textarea
              id="deck-description"
              v-model="deckDescription"
              rows="3"
              class="input-field w-full"
              placeholder="Enter deck description"
              :disabled="saving"
            />
          </div>

          <!-- Action Buttons -->
          <div class="flex space-x-4">
            <GameButton
              type="submit"
              variant="primary"
              :disabled="saving || !canSave"
              class="flex-1"
            >
              {{ saving ? 'Saving...' : (isEditMode ? 'Update Deck' : 'Create Deck') }}
            </GameButton>
            <GameButton
              type="button"
              variant="secondary"
              @click="cancel"
              :disabled="saving"
              class="flex-1"
            >
              Cancel
            </GameButton>
          </div>
        </form>
      </Panel>

      <!-- Loading state -->
      <div v-if="loading" class="text-center py-8">
        <p class="text-gray-600">Loading...</p>
      </div>

      <!-- Error state -->
      <div v-if="error" class="text-center py-8">
        <h2 class="text-2xl font-bold text-red-600 mb-4">Error</h2>
        <p class="text-gray-600">{{ error }}</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTitleStore } from '../stores/title'
import { useNotificationStore } from '../stores/notifications'
import axios from '../config/api'
import Panel from '../components/layout/Panel.vue'
import GameButton from '../components/ui/GameButton.vue'

interface HeroData {
  id: number
  slug: string
  name: string
  health: number
  hero_power: any
  spec: any
  faction: string | null
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
}

const route = useRoute()
const router = useRouter()
const titleStore = useTitleStore()
const notificationStore = useNotificationStore()

// Component state
const loading = ref<boolean>(true)
const error = ref<string | null>(null)
const saving = ref<boolean>(false)
const heroesLoading = ref<boolean>(false)

// Form data
const deckName = ref<string>('')
const deckDescription = ref<string>('')
const selectedHeroId = ref<number | null>(null)
const heroes = ref<HeroData[]>([])

// Computed properties
const titleData = computed(() => titleStore.currentTitle)
const titleSlug = computed(() => route.params.slug as string)
const deckId = computed(() => route.params.id as string)
const isEditMode = computed(() => !!deckId.value)

const canSave = computed(() => {
  return deckName.value.trim() && selectedHeroId.value && !heroesLoading.value
})

// Methods
const fetchHeroes = async (): Promise<void> => {
  try {
    heroesLoading.value = true
    const response = await axios.get(`/titles/${titleSlug.value}/heroes/`)
    heroes.value = response.data
  } catch (err) {
    console.error('Error fetching heroes:', err)
    error.value = 'Failed to load heroes'
  } finally {
    heroesLoading.value = false
  }
}

const fetchDeck = async (): Promise<void> => {
  if (!isEditMode.value) return

  try {
    const response = await axios.get(`/collection/decks/${deckId.value}/`)
    const deck: DeckData = response.data

    deckName.value = deck.name
    deckDescription.value = deck.description
    selectedHeroId.value = deck.hero.id
  } catch (err) {
    console.error('Error fetching deck:', err)
    if (err.response?.status === 404) {
      error.value = 'Deck not found'
    } else {
      error.value = 'Failed to load deck'
    }
  }
}

const saveDeck = async (): Promise<void> => {
  if (!canSave.value) return

  try {
    saving.value = true

    const deckData = {
      name: deckName.value.trim(),
      description: deckDescription.value.trim(),
      hero_id: selectedHeroId.value
    }

    let response
    if (isEditMode.value) {
      response = await axios.put(`/collection/decks/${deckId.value}/`, deckData)
    } else {
      response = await axios.post(`/collection/titles/${titleSlug.value}/decks/`, deckData)
    }

    notificationStore.handleApiSuccess(response)

    // Navigate to the deck detail page
    const newDeckId = response.data.id || deckId.value
    router.push({
      name: 'DeckDetail',
      params: {
        slug: titleSlug.value,
        id: newDeckId
      }
    })
  } catch (err) {
    console.error('Error saving deck:', err)
    notificationStore.handleApiError(err)
  } finally {
    saving.value = false
  }
}

const cancel = (): void => {
  if (isEditMode.value) {
    // Go back to deck detail page
    router.push({
      name: 'DeckDetail',
      params: {
        slug: titleSlug.value,
        id: deckId.value
      }
    })
  } else {
    // Go back to title page
    router.push({
      name: 'Title',
      params: { slug: titleSlug.value }
    })
  }
}

// Lifecycle
onMounted(async () => {
  try {
    loading.value = true

    // Fetch heroes first
    await fetchHeroes()

    // If editing, fetch the deck data
    if (isEditMode.value) {
      await fetchDeck()
    }
  } catch (err) {
    console.error('Error initializing deck edit:', err)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.deck-edit-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
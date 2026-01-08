<template>
  <div class="deck-edit-page">
    <section class="relative bg-gray-300 overflow-hidden h-24 flex items-center justify-center">
      <h1 class="font-display text-4xl font-bold dark:text-gray-900">
        {{ isEditMode ? 'Edit Deck' : 'New Deck' }}
      </h1>
    </section>

    <main class="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8 mt-10">
      <Panel
        padding="lg"
        customClass="mx-auto w-full max-w-3xl border border-white/50 bg-white/80 backdrop-blur-lg shadow-xl dark:border-gray-800/80 dark:bg-gray-900/80"
      >
        <form @submit.prevent="saveDeck" class="mx-auto flex w-full max-w-2xl flex-col gap-10">
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
          <fieldset class="space-y-4">
            <legend class="text-sm font-medium text-gray-700 dark:text-gray-300">
              Hero
            </legend>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              <template v-if="selectedHero">
                Selected hero:
                <span class="font-medium text-gray-900 dark:text-gray-200">
                  {{ selectedHero.name }}
                </span>
              </template>
              <template v-else>
                Choose a hero to unlock deck abilities.
              </template>
            </p>

            <div v-if="heroesLoading" class="flex items-center justify-center rounded-2xl border border-dashed border-gray-300 py-10 text-gray-500 dark:border-gray-700 dark:text-gray-400">
              Loading heroes…
            </div>

            <div
              v-else-if="heroes.length"
              class="grid gap-4 sm:grid-cols-2"
              role="radiogroup"
              aria-label="Hero selection"
            >
              <button
                v-for="hero in heroes"
                :key="hero.id"
                type="button"
                class="group relative flex flex-col gap-4 rounded-2xl border border-gray-200 bg-white/80 px-5 py-4 text-left shadow-sm transition-all hover:-translate-y-1 hover:border-primary-400 hover:shadow-primary-200/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400 dark:border-gray-800 dark:bg-gray-800/70 dark:hover:border-primary-500/70"
                :class="{
                  'ring-2 ring-primary-500 ring-offset-2 ring-offset-white dark:ring-offset-gray-900': isHeroSelected(hero.id),
                  'cursor-not-allowed opacity-60': saving
                }"
                role="radio"
                :aria-checked="isHeroSelected(hero.id)"
                :aria-disabled="saving"
                :disabled="saving"
                @click="selectHero(hero.id)"
              >
                <div class="flex items-center justify-between gap-4">
                  <div class="space-y-1">
                    <h3 class="font-display text-xl font-semibold text-gray-900 dark:text-white">
                      {{ hero.name }}
                    </h3>
                  </div>
                  <div class="flex flex-col items-center rounded-xl bg-gray-900/90 px-4 py-2 text-white shadow-inner dark:bg-gray-700/90">
                    <span class="text-[10px] uppercase tracking-wider text-gray-300 dark:text-gray-200">Health</span>
                    <span class="text-lg font-semibold">{{ hero.health }}</span>
                  </div>
                </div>
                <p class="min-h-[2.75rem] text-sm leading-relaxed text-gray-600 transition-colors dark:text-gray-300">
                  {{ hero.hero_power?.description || hero.hero_power?.name || 'Battle-hardened leader ready for your strategy.' }}
                </p>
              </button>
            </div>

            <div v-else class="rounded-2xl border border-dashed border-gray-300 px-4 py-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
              No heroes available for this title yet.
            </div>
          </fieldset>

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
          <div class="flex flex-col gap-3 sm:flex-row">
            <GameButton
              type="submit"
              variant="primary"
              :disabled="saving"
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
import { isAxiosError } from 'axios'
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
const titleSlug = computed(() => route.params.slug as string)
const deckId = computed(() => route.params.id as string)
const isEditMode = computed(() => !!deckId.value)

const selectedHero = computed<HeroData | null>(() => {
  if (selectedHeroId.value === null) return null
  return heroes.value.find(hero => hero.id === selectedHeroId.value) ?? null
})

const canSave = computed(() => {
  return Boolean(deckName.value.trim()) && selectedHeroId.value !== null && !heroesLoading.value
})

// Methods
const fetchHeroes = async (): Promise<void> => {
  try {
    heroesLoading.value = true
    const response = await axios.get(`/titles/${titleSlug.value}/heroes/`)
    heroes.value = response.data
  } catch (err: unknown) {
    console.error('Error fetching heroes:', err)
    if (isAxiosError(err) && err.response?.data && typeof err.response.data === 'object') {
      const data = err.response.data as Record<string, unknown>
      if (typeof data.detail === 'string') {
        error.value = data.detail
        return
      }
    }
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
  } catch (err: unknown) {
    console.error('Error fetching deck:', err)
    if (isAxiosError(err)) {
      if (err.response?.status === 404) {
        error.value = 'Deck not found'
        return
      }
      if (err.response?.data && typeof err.response.data === 'object') {
        const data = err.response.data as Record<string, unknown>
        if (typeof data.detail === 'string') {
          error.value = data.detail
          return
        }
      }
    }
    error.value = 'Failed to load deck'
  }
}

const saveDeck = async (): Promise<void> => {
  // Validate form inputs
  if (!deckName.value.trim()) {
    notificationStore.error('Deck name is required')
    return
  }

  if (selectedHeroId.value === null) {
    notificationStore.error('Please select a hero for your deck')
    return
  }

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
  } catch (err: unknown) {
    console.error('Error saving deck:', err)
    if (isAxiosError(err) || err instanceof Error) {
      notificationStore.handleApiError(err)
    } else {
      notificationStore.handleApiError(new Error('Unknown error saving deck'))
    }
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

const selectHero = (heroId: number): void => {
  if (saving.value) return
  selectedHeroId.value = heroId
}

const isHeroSelected = (heroId: number): boolean => selectedHeroId.value === heroId

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
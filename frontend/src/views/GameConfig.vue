<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <main class="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <header class="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 class="font-display text-3xl font-bold text-gray-900 dark:text-white">
            Game Config
          </h1>
          <p class="mt-2 text-sm text-gray-600 dark:text-gray-300">
            {{ title?.name || 'World' }}
          </p>
        </div>

        <div class="flex items-center gap-3">
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
            :disabled="loading || saving || !loadedConfig"
            @click="resetForm"
          >
            <RotateCcw class="h-4 w-4" aria-hidden="true" />
            Reset
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="!canSave"
            @click="saveConfig"
          >
            <Loader2 v-if="saving" class="h-4 w-4 animate-spin" aria-hidden="true" />
            <Save v-else class="h-4 w-4" aria-hidden="true" />
            {{ saving ? 'Saving' : 'Save' }}
          </button>
        </div>
      </header>

      <div v-if="loading" class="flex min-h-64 items-center justify-center rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
        <Loader2 class="h-6 w-6 animate-spin text-primary-600" aria-hidden="true" />
      </div>

      <div v-else-if="error" class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">
        {{ error }}
      </div>

      <form v-else class="space-y-8" @submit.prevent="saveConfig">
        <section class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div class="mb-6 flex items-center gap-3">
            <Settings class="h-5 w-5 text-primary-600" aria-hidden="true" />
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Deck Rules</h2>
          </div>

          <div class="grid gap-5 md:grid-cols-3">
            <label class="block">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Max cards per deck</span>
              <input
                v-model.number="form.deck_size_limit"
                type="number"
                min="1"
                step="1"
                class="mt-2 block w-full rounded-lg border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white"
              />
            </label>

            <label class="block">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Min cards per deck</span>
              <input
                v-model.number="form.min_cards_in_deck"
                type="number"
                min="0"
                step="1"
                class="mt-2 block w-full rounded-lg border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white"
              />
            </label>

            <label class="block">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Max copies per card</span>
              <input
                v-model.number="form.deck_card_max_count"
                type="number"
                min="1"
                step="1"
                class="mt-2 block w-full rounded-lg border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white"
              />
            </label>
          </div>
        </section>

        <section class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div class="mb-6 flex items-center gap-3">
            <SlidersHorizontal class="h-5 w-5 text-primary-600" aria-hidden="true" />
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Opening And Turns</h2>
          </div>

          <div class="grid gap-5 md:grid-cols-3">
            <label class="block">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Starting hand size</span>
              <input
                v-model.number="form.hand_start_size"
                type="number"
                min="0"
                step="1"
                class="mt-2 block w-full rounded-lg border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white"
              />
            </label>

            <label class="block">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Rapid turn timer seconds</span>
              <input
                v-model.number="form.ranked_time_per_turn"
                type="number"
                min="0"
                step="1"
                class="mt-2 block w-full rounded-lg border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white"
              />
            </label>

            <label class="block">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Side B compensation slug</span>
              <input
                v-model.trim="form.side_b_compensation"
                type="text"
                class="mt-2 block w-full rounded-lg border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white"
                placeholder="none"
              />
            </label>
          </div>

          <label class="mt-6 flex items-center gap-3">
            <input
              v-model="form.death_retaliation"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-900"
            />
            <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Death retaliation</span>
          </label>
        </section>

        <div
          v-if="validationError"
          class="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200"
        >
          <AlertCircle class="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
          <span>{{ validationError }}</span>
        </div>
      </form>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { AlertCircle, Loader2, RotateCcw, Save, Settings, SlidersHorizontal } from 'lucide-vue-next'
import axios from '../config/api'
import { useNotificationStore } from '../stores/notifications'
import { useTitleStore } from '../stores/title'

interface GameConfigForm {
  deck_size_limit: number
  min_cards_in_deck: number
  deck_card_max_count: number
  hand_start_size: number
  side_b_compensation: string
  death_retaliation: boolean
  ranked_time_per_turn: number
}

interface GameConfigResponse {
  config: Omit<GameConfigForm, 'side_b_compensation'> & {
    side_b_compensation: string | null
  }
}

const defaultConfig: GameConfigForm = {
  deck_size_limit: 30,
  min_cards_in_deck: 10,
  deck_card_max_count: 9,
  hand_start_size: 3,
  side_b_compensation: '',
  death_retaliation: false,
  ranked_time_per_turn: 60
}

const route = useRoute()
const titleStore = useTitleStore()
const notificationStore = useNotificationStore()

const title = computed(() => titleStore.currentTitle)
const slug = computed(() => route.params.slug as string)
const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const loadedConfig = ref<GameConfigForm | null>(null)
const form = reactive<GameConfigForm>({ ...defaultConfig })

const normalizeConfig = (config: GameConfigResponse['config']): GameConfigForm => ({
  deck_size_limit: config.deck_size_limit,
  min_cards_in_deck: config.min_cards_in_deck,
  deck_card_max_count: config.deck_card_max_count,
  hand_start_size: config.hand_start_size,
  side_b_compensation: config.side_b_compensation || '',
  death_retaliation: config.death_retaliation,
  ranked_time_per_turn: config.ranked_time_per_turn
})

const applyConfig = (config: GameConfigForm): void => {
  Object.assign(form, config)
}

const validationError = computed(() => {
  if (form.deck_size_limit < 1) return 'Max cards per deck must be at least 1.'
  if (form.min_cards_in_deck < 0) return 'Min cards per deck cannot be negative.'
  if (form.min_cards_in_deck > form.deck_size_limit) {
    return 'Min cards per deck cannot exceed max cards per deck.'
  }
  if (form.deck_card_max_count < 1) return 'Max copies per card must be at least 1.'
  if (form.hand_start_size < 0) return 'Starting hand size cannot be negative.'
  if (form.hand_start_size > form.deck_size_limit) {
    return 'Starting hand size cannot exceed max cards per deck.'
  }
  if (form.ranked_time_per_turn < 0) return 'Rapid turn timer seconds cannot be negative.'
  return null
})

const canSave = computed(() => {
  return !loading.value && !saving.value && !validationError.value && !!loadedConfig.value
})

const fetchConfig = async (): Promise<void> => {
  try {
    loading.value = true
    error.value = null
    const response = await axios.get<GameConfigResponse>(`/builder/titles/${slug.value}/config/`)
    const config = normalizeConfig(response.data.config)
    loadedConfig.value = { ...config }
    applyConfig(config)
  } catch (err) {
    console.error('Error loading game config:', err)
    error.value = 'Failed to load game config.'
    notificationStore.handleApiError(err as Error)
  } finally {
    loading.value = false
  }
}

const resetForm = (): void => {
  if (!loadedConfig.value) return
  applyConfig({ ...loadedConfig.value })
}

const saveConfig = async (): Promise<void> => {
  if (!canSave.value) return

  try {
    saving.value = true
    const payload = {
      ...form,
      side_b_compensation: form.side_b_compensation.trim() || null
    }
    const response = await axios.put<GameConfigResponse>(`/builder/titles/${slug.value}/config/`, {
      config: payload
    })
    const savedConfig = normalizeConfig(response.data.config)
    loadedConfig.value = { ...savedConfig }
    applyConfig(savedConfig)
    notificationStore.success('Game config saved')
  } catch (err) {
    console.error('Error saving game config:', err)
    notificationStore.handleApiError(err as Error)
  } finally {
    saving.value = false
  }
}

onMounted(fetchConfig)

watch(slug, () => {
  void fetchConfig()
})
</script>

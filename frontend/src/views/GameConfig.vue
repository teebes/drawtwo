<template>
  <div class="ui-page">
    <main class="ui-page-container ui-page-container-narrow">
      <header class="ui-page-header-row">
        <div>
          <h1 class="ui-page-title">
            Game Config
          </h1>
          <p class="ui-page-meta">
            {{ title?.name || 'World' }}
          </p>
        </div>

        <div class="flex items-center gap-3">
          <button
            type="button"
            class="ui-btn ui-btn-md ui-btn-secondary"
            :disabled="loading || saving || !loadedConfig"
            @click="resetForm"
          >
            <RotateCcw class="h-4 w-4" aria-hidden="true" />
            Reset
          </button>
          <button
            type="button"
            class="ui-btn ui-btn-md ui-btn-primary"
            :disabled="!canSave"
            @click="saveConfig"
          >
            <Loader2 v-if="saving" class="h-4 w-4 animate-spin" aria-hidden="true" />
            <Save v-else class="h-4 w-4" aria-hidden="true" />
            {{ saving ? 'Saving' : 'Save' }}
          </button>
        </div>
      </header>

      <div v-if="loading" class="ui-panel min-h-64 items-center justify-center">
        <Loader2 class="h-6 w-6 animate-spin text-primary-600" aria-hidden="true" />
      </div>

      <div v-else-if="error" class="ui-alert ui-alert-error">
        {{ error }}
      </div>

      <form v-else class="space-y-8" @submit.prevent="saveConfig">
        <section class="ui-panel">
          <div class="ui-panel-heading">
            <Settings class="ui-panel-icon" aria-hidden="true" />
            <h2 class="ui-panel-title">Deck Rules</h2>
          </div>

          <div class="grid gap-5 md:grid-cols-3">
            <label class="block">
              <span class="ui-label">Max cards per deck</span>
              <input
                v-model.number="form.deck_size_limit"
                type="number"
                min="1"
                step="1"
                class="ui-input mt-2"
              />
            </label>

            <label class="block">
              <span class="ui-label">Min cards per deck</span>
              <input
                v-model.number="form.min_cards_in_deck"
                type="number"
                min="0"
                step="1"
                class="ui-input mt-2"
              />
            </label>

            <label class="block">
              <span class="ui-label">Max copies per card</span>
              <input
                v-model.number="form.deck_card_max_count"
                type="number"
                min="1"
                step="1"
                class="ui-input mt-2"
              />
            </label>
          </div>
        </section>

        <section class="ui-panel">
          <div class="ui-panel-heading">
            <SlidersHorizontal class="ui-panel-icon" aria-hidden="true" />
            <h2 class="ui-panel-title">Opening And Turns</h2>
          </div>

          <div class="grid gap-5 md:grid-cols-3">
            <label class="block">
              <span class="ui-label">Starting hand size</span>
              <input
                v-model.number="form.hand_start_size"
                type="number"
                min="0"
                step="1"
                class="ui-input mt-2"
              />
            </label>

            <label class="block">
              <span class="ui-label">Rapid turn timer seconds</span>
              <input
                v-model.number="form.ranked_time_per_turn"
                type="number"
                min="0"
                step="1"
                class="ui-input mt-2"
              />
            </label>

            <label class="block">
              <span class="ui-label">Side B compensation slug</span>
              <input
                v-model.trim="form.side_b_compensation"
                type="text"
                class="ui-input mt-2"
                placeholder="none"
              />
            </label>
          </div>

          <label class="mt-6 flex items-center gap-3">
            <input
              v-model="form.death_retaliation"
              type="checkbox"
              class="ui-checkbox"
            />
            <span class="ui-label">Death retaliation</span>
          </label>
        </section>

        <div
          v-if="validationError"
          class="ui-alert ui-alert-warning flex items-start gap-3"
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

<template>
  <div class="ui-page">
    <BaseModal :show="exportModalOpen" @close="closeExportModal">
      <div class="p-6">
        <div class="mb-4 flex items-start justify-between gap-4 pr-8">
          <div>
            <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
              Export Title Snapshot
            </h2>
            <p v-if="snapshotCountLabel" class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {{ snapshotCountLabel }}
            </p>
          </div>
          <button
            type="button"
            :disabled="snapshotLoading || Boolean(snapshotError) || !snapshotYaml"
            :class="[
              'ui-btn ui-btn-sm',
              snapshotCopied
                ? 'border border-green-300 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950/40 dark:text-green-200'
                : 'ui-btn-secondary'
            ]"
            @click="copySnapshotYaml"
          >
            <Check v-if="snapshotCopied" class="h-4 w-4" aria-hidden="true" />
            <Copy v-else class="h-4 w-4" aria-hidden="true" />
            {{ snapshotCopied ? 'Copied' : 'Copy' }}
          </button>
        </div>

        <div v-if="snapshotLoading" class="flex items-center justify-center gap-3 py-12 text-gray-500 dark:text-gray-400">
          <Loader2 class="h-5 w-5 animate-spin" aria-hidden="true" />
          <span>Loading YAML...</span>
        </div>
        <div v-else-if="snapshotError" class="ui-alert ui-alert-error">
          {{ snapshotError }}
        </div>
        <pre v-else class="max-h-[60vh] overflow-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100 dark:bg-gray-950"><code>{{ snapshotYaml }}</code></pre>
      </div>
    </BaseModal>

    <BaseModal :show="importModalOpen" @close="closeImportModal">
      <div class="p-6">
        <div class="mb-5 pr-8">
          <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
            Import YAML
          </h2>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {{ title?.name || 'World' }}
          </p>
        </div>

        <div class="space-y-5">
          <label class="block">
            <span class="ui-label">YAML content</span>
            <textarea
              v-model="importYamlContent"
              rows="16"
              class="ui-input mt-2 min-h-80 font-mono"
              placeholder="- type: title"
              :disabled="importing"
            />
          </label>

          <label class="flex items-start gap-3">
            <input
              v-model="replaceMissing"
              type="checkbox"
              class="ui-checkbox mt-0.5"
              :disabled="importing"
            />
            <span>
              <span class="ui-label">Replace missing snapshot content</span>
              <span class="ui-help block">Use for prod/local cloning; leave off for additive card promotion.</span>
            </span>
          </label>

          <div v-if="importError" class="ui-alert ui-alert-error">
            {{ importError }}
          </div>

          <div v-if="importResults.length || removedResources.length" class="space-y-4">
            <div v-if="importResults.length" class="ui-alert ui-alert-success">
              Processed {{ importResults.length }} resource{{ importResults.length === 1 ? '' : 's' }}.
            </div>

            <div v-if="importResults.length" class="max-h-56 overflow-auto rounded-lg border border-gray-200 dark:border-gray-700">
              <div
                v-for="resource in importResults"
                :key="`${resource.resource_type}-${resource.slug}-${resource.name}`"
                class="flex items-center justify-between gap-3 border-b border-gray-200 px-3 py-2 last:border-b-0 dark:border-gray-700"
              >
                <div>
                  <div class="text-sm font-medium text-gray-900 dark:text-white">
                    {{ resource.name }}
                  </div>
                  <div class="text-xs text-gray-500 dark:text-gray-400">
                    {{ resourceTypeLabel(resource.resource_type) }}
                    <span v-if="resource.slug"> - {{ resource.slug }}</span>
                  </div>
                </div>
                <span
                  :class="[
                    'ui-status-badge',
                    resource.action === 'created' ? 'ui-status-success' : 'ui-status-info'
                  ]"
                >
                  {{ resource.action }}
                </span>
              </div>
            </div>

            <div v-if="removedResources.length" class="ui-alert ui-alert-warning">
              Removed {{ removedResources.length }} missing resource{{ removedResources.length === 1 ? '' : 's' }}.
            </div>
          </div>

          <div class="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button
              type="button"
              class="ui-btn ui-btn-md ui-btn-secondary"
              :disabled="importing"
              @click="clearImport"
            >
              Clear
            </button>
            <button
              type="button"
              class="ui-btn ui-btn-md ui-btn-primary"
              :disabled="importing || !importYamlContent.trim()"
              @click="importSnapshotYaml"
            >
              <Loader2 v-if="importing" class="h-4 w-4 animate-spin" aria-hidden="true" />
              <Upload v-else class="h-4 w-4" aria-hidden="true" />
              {{ importing ? 'Importing' : 'Import YAML' }}
            </button>
          </div>
        </div>
      </div>
    </BaseModal>

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

        <div class="flex flex-wrap items-center gap-3">
          <button
            type="button"
            class="ui-btn ui-btn-md ui-btn-secondary"
            :disabled="loading || saving"
            @click="openImportModal"
          >
            <Upload class="h-4 w-4" aria-hidden="true" />
            Import YAML
          </button>
          <button
            type="button"
            class="ui-btn ui-btn-md ui-btn-secondary"
            :disabled="loading || saving"
            @click="openExportModal"
          >
            <Download class="h-4 w-4" aria-hidden="true" />
            Export YAML
          </button>
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

        <section class="ui-panel">
          <div class="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div class="ui-panel-heading mb-2">
                <BookOpen class="ui-panel-icon" aria-hidden="true" />
                <h2 class="ui-panel-title">Heroes & Cards</h2>
              </div>
              <p class="ui-panel-subtitle">
                Manage the title's playable heroes and card library.
              </p>
            </div>

            <router-link
              :to="{ name: 'GameContentConfig', params: { slug } }"
              class="ui-btn ui-btn-md ui-btn-secondary self-start sm:self-auto"
            >
              Open Content
              <ArrowRight class="h-4 w-4" aria-hidden="true" />
            </router-link>
          </div>
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
import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  Check,
  Copy,
  Download,
  Loader2,
  RotateCcw,
  Save,
  Settings,
  SlidersHorizontal,
  Upload
} from 'lucide-vue-next'
import axios from '../config/api'
import BaseModal from '../components/modals/BaseModal.vue'
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

interface SnapshotCounts {
  resources: number
  cards: number
  heroes: number
  decks: number
}

interface SnapshotResponse {
  yaml: string
  counts?: SnapshotCounts
}

type SnapshotResourceType =
  | 'title'
  | 'config'
  | 'faction'
  | 'tag'
  | 'trait_override'
  | 'hero'
  | 'card'
  | 'deck'

interface SnapshotResource {
  resource_type: SnapshotResourceType
  action: 'created' | 'updated'
  id: number
  slug: string
  name: string
}

interface RemovedResource {
  resource_type: SnapshotResourceType
  slug: string
  name: string
}

interface SnapshotImportResponse {
  resources: SnapshotResource[]
  removed: RemovedResource[]
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

const exportModalOpen = ref(false)
const snapshotYaml = ref('')
const snapshotCounts = ref<SnapshotCounts | null>(null)
const snapshotLoading = ref(false)
const snapshotError = ref<string | null>(null)
const snapshotCopied = ref(false)

const importModalOpen = ref(false)
const importYamlContent = ref('')
const replaceMissing = ref(false)
const importing = ref(false)
const importError = ref<string | null>(null)
const importResults = ref<SnapshotResource[]>([])
const removedResources = ref<RemovedResource[]>([])

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

const snapshotCountLabel = computed(() => {
  if (!snapshotCounts.value) return ''
  const { resources, cards, heroes, decks } = snapshotCounts.value
  return `${resources} resources - ${heroes} heroes, ${cards} cards, ${decks} AI decks`
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

const openExportModal = async (): Promise<void> => {
  exportModalOpen.value = true
  snapshotYaml.value = ''
  snapshotCounts.value = null
  snapshotError.value = null
  snapshotCopied.value = false

  try {
    snapshotLoading.value = true
    const response = await axios.get<SnapshotResponse>(`/builder/titles/${slug.value}/snapshot/`)
    snapshotYaml.value = response.data.yaml
    snapshotCounts.value = response.data.counts || null
  } catch (err: any) {
    snapshotError.value = err.response?.data?.error || err.message || 'Failed to export YAML.'
    console.error('Error exporting title snapshot:', err)
  } finally {
    snapshotLoading.value = false
  }
}

const closeExportModal = (): void => {
  exportModalOpen.value = false
  snapshotYaml.value = ''
  snapshotCounts.value = null
  snapshotError.value = null
  snapshotCopied.value = false
}

const openImportModal = (): void => {
  importModalOpen.value = true
  importError.value = null
}

const closeImportModal = (): void => {
  if (importing.value) return
  importModalOpen.value = false
  importError.value = null
  importResults.value = []
  removedResources.value = []
}

const clearImport = (): void => {
  importYamlContent.value = ''
  importError.value = null
  importResults.value = []
  removedResources.value = []
}

const importSnapshotYaml = async (): Promise<void> => {
  if (!importYamlContent.value.trim()) return

  try {
    importing.value = true
    importError.value = null
    importResults.value = []
    removedResources.value = []

    const response = await axios.post<SnapshotImportResponse>(`/builder/titles/${slug.value}/snapshot/`, {
      yaml_content: importYamlContent.value,
      replace_missing: replaceMissing.value
    })

    importResults.value = response.data.resources || []
    removedResources.value = response.data.removed || []
    importYamlContent.value = ''

    const importedTitle = importResults.value.find(resource => resource.resource_type === 'title')
    if (importedTitle && titleStore.currentTitle) {
      titleStore.setCurrentTitle({
        ...titleStore.currentTitle,
        name: importedTitle.name
      })
    }

    await fetchConfig()
    notificationStore.success('YAML import completed')
  } catch (err: any) {
    importError.value = err.response?.data?.error || err.message || 'Failed to import YAML.'
    console.error('Error importing title snapshot:', err)
    notificationStore.handleApiError(err as Error)
  } finally {
    importing.value = false
  }
}

const writeTextWithTextarea = (text: string): boolean => {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.top = '-9999px'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()

  const copiedToClipboard = document.execCommand('copy')
  document.body.removeChild(textarea)

  return copiedToClipboard
}

const writeTextToClipboard = async (text: string): Promise<void> => {
  if (writeTextWithTextarea(text)) return

  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }

  throw new Error('Unable to copy text.')
}

const copySnapshotYaml = async (): Promise<void> => {
  if (!snapshotYaml.value) return

  try {
    await writeTextToClipboard(snapshotYaml.value)
    snapshotCopied.value = true
    setTimeout(() => {
      snapshotCopied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy YAML:', err)
    notificationStore.error('Failed to copy YAML.')
  }
}

const resourceTypeLabel = (type: SnapshotResourceType): string => {
  return type.replace('_', ' ')
}

onMounted(fetchConfig)

watch(slug, () => {
  closeExportModal()
  closeImportModal()
  void fetchConfig()
})
</script>

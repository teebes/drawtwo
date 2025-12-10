<template>
  <div v-if="title" class="title-edit-page min-h-screen bg-gray-50 dark:bg-gray-900">
    <section class="banner">
      <h1>Edit</h1>
    </section>

    <main class="mx-auto w-full max-w-4xl px-4 sm:px-6 lg:px-8 pb-16 space-y-8">

      <GameButton class="mt-8" variant="secondary" size="xs" @click="openYamlModal">
        WORLD CONFIG
      </GameButton>

      <!-- YAML Modal -->
      <BaseModal :show="yamlModalOpen" @close="closeYamlModal">
        <div class="p-6">
          <!-- Header -->
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
              Title Configuration YAML
            </h2>
            <button
              @click="copyYaml"
              class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-lg transition-colors"
              :class="copied
                ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'"
            >
              <svg v-if="!copied" class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <svg v-else class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              {{ copied ? 'Copied!' : 'Copy' }}
            </button>
          </div>

          <!-- Content -->
          <div v-if="yamlLoading" class="flex items-center justify-center py-12">
            <p class="text-gray-500 dark:text-gray-400">Loading YAML...</p>
          </div>
          <div v-else-if="yamlError" class="text-red-600 dark:text-red-400 py-4">
            {{ yamlError }}
          </div>
          <div v-else>
            <pre class="bg-gray-900 dark:bg-gray-950 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono max-h-96 overflow-y-auto"><code>{{ configYamlContent }}</code></pre>
            <p class="mt-3 text-xs text-gray-500 dark:text-gray-400">
              Copy this YAML and paste it into the ingestion tool to update the title configuration or use as a template.
            </p>
          </div>
        </div>
      </BaseModal>

      <!-- YAML Manifest Ingestion Section -->
      <Section class="mt-8" title="Add / Edit Resources" subtitle="Create or update cards, heroes, and decks by pasting YAML content below.">
        <Panel>
          <div class="space-y-4">
            <div>
              <label for="yaml-input" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                YAML Content
              </label>
              <textarea
                id="yaml-input"
                v-model="yamlContent"
                rows="20"
                class="block w-full rounded-lg border-gray-300 font-mono text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 py-3 px-4"
                :placeholder="yamlPlaceholder"
                :disabled="ingesting"
              />
            </div>

            <div class="flex items-center justify-between">
              <p class="text-xs text-gray-500 dark:text-gray-400">
                Supports cards, heroes, and decks. Use <code class="bg-gray-100 dark:bg-gray-600 px-1 rounded">type: card</code>,
                <code class="bg-gray-100 dark:bg-gray-600 px-1 rounded">type: hero</code>, or
                <code class="bg-gray-100 dark:bg-gray-600 px-1 rounded">type: deck</code> to specify the resource type.
              </p>
              <div class="flex space-x-3">
                <GameButton
                  variant="secondary"
                  @click="clearYaml"
                  :disabled="ingesting || !yamlContent"
                >
                  Clear
                </GameButton>
                <GameButton
                  variant="primary"
                  @click="ingestYaml"
                  :disabled="ingesting || !yamlContent.trim()"
                >
                  {{ ingesting ? 'Processing...' : 'Ingest YAML' }}
                </GameButton>
              </div>
            </div>
          </div>
        </Panel>
      </Section>

      <!-- Error Display -->
      <Panel v-if="error" variant="error" title="Error">
        <p class="text-red-600 dark:text-red-400">{{ error }}</p>
      </Panel>

      <!-- Success Results -->
      <Section v-if="results.length > 0" title="Ingestion Results">
        <Panel variant="success">
          <p class="mb-4 text-green-700 dark:text-green-300">
            Successfully processed {{ results.length }} resource(s).
          </p>

          <div class="space-y-2">
            <div
              v-for="(resource, index) in results"
              :key="index"
              class="flex items-center justify-between rounded-lg bg-white/50 dark:bg-gray-800/50 p-3 border border-green-300/30 dark:border-green-500/30"
            >
              <div class="flex items-center space-x-3">
                <!-- Resource Type Icon -->
                <span class="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full" :class="getResourceIconClass(resource.resource_type)">
                  <span v-if="resource.resource_type === 'card'">🃏</span>
                  <span v-else-if="resource.resource_type === 'hero'">⚔️</span>
                  <span v-else-if="resource.resource_type === 'deck'">📚</span>
                </span>

                <div>
                  <div class="font-medium text-gray-900 dark:text-white">
                    {{ resource.name }}
                  </div>
                  <div class="text-xs text-gray-500 dark:text-gray-400">
                    <span class="capitalize">{{ resource.resource_type }}</span>
                    <span class="mx-1">•</span>
                    <span :class="resource.action === 'created' ? 'text-green-600 dark:text-green-400' : 'text-blue-600 dark:text-blue-400'">
                      {{ resource.action }}
                    </span>
                    <span v-if="resource.slug" class="mx-1">•</span>
                    <code v-if="resource.slug" class="bg-gray-100 dark:bg-gray-700 px-1 rounded text-xs">{{ resource.slug }}</code>
                  </div>
                </div>
              </div>

              <!-- Link to Resource -->
              <router-link
                v-if="getResourceLink(resource)"
                :to="getResourceLink(resource)!"
                class="inline-flex items-center rounded-lg bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
              >
                View
                <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                </svg>
              </router-link>
            </div>
          </div>
        </Panel>
      </Section>

    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTitleStore } from '@/stores/title'
import axios from '@/config/api'
import Section from '@/components/layout/Section.vue'
import Panel from '@/components/layout/Panel.vue'
import GameButton from '@/components/ui/GameButton.vue'
import BaseModal from '@/components/modals/BaseModal.vue'

interface IngestedResource {
  resource_type: 'card' | 'hero' | 'deck'
  action: 'created' | 'updated'
  id: number
  slug: string
  name: string
}

const titleStore = useTitleStore()
const title = computed(() => titleStore.currentTitle)

const yamlContent = ref('')
const ingesting = ref(false)
const error = ref<string | null>(null)
const results = ref<IngestedResource[]>([])

// YAML Modal state
const yamlModalOpen = ref(false)
const configYamlContent = ref('')
const yamlLoading = ref(false)
const yamlError = ref<string | null>(null)
const copied = ref(false)

const yamlPlaceholder = `# Example YAML format for ingestion

# Create a hero
- type: hero
  slug: warrior
  name: Warrior
  description: A mighty warrior hero.
  health: 30
  hero_power:
    name: Strike
    description: Deal 1 damage to an enemy.
    actions:
      - action: damage
        amount: 1
        target: enemy

# Create a card
- type: card
  card_type: creature
  slug: footman
  name: Footman
  description: A basic soldier.
  cost: 1
  attack: 1
  health: 2
  traits:
    - type: taunt

# Create a deck
- type: deck
  name: Starter Deck
  hero: warrior
  cards:
    - card: footman
      count: 4`

const ingestYaml = async () => {
  if (!title.value || !yamlContent.value.trim()) return

  try {
    ingesting.value = true
    error.value = null
    results.value = []

    const response = await axios.post(`/builder/titles/${title.value.slug}/ingest/`, {
      yaml_content: yamlContent.value
    })

    results.value = response.data.resources || []

    // Clear the textarea on success
    yamlContent.value = ''

  } catch (err: any) {
    error.value = err.response?.data?.error || err.message || 'Failed to ingest YAML'
    console.error('Error ingesting YAML:', err)
  } finally {
    ingesting.value = false
  }
}

const clearYaml = () => {
  yamlContent.value = ''
  error.value = null
}

const getResourceIconClass = (resourceType: string): string => {
  switch (resourceType) {
    case 'card':
      return 'bg-secondary-100 dark:bg-secondary-900'
    case 'hero':
      return 'bg-red-100 dark:bg-red-900'
    case 'deck':
      return 'bg-primary-100 dark:bg-primary-900'
    default:
      return 'bg-gray-100 dark:bg-gray-900'
  }
}

const getResourceLink = (resource: IngestedResource): object | null => {
  if (!title.value) return null

  switch (resource.resource_type) {
    case 'card':
      return {
        name: 'CardDetails',
        params: {
          slug: title.value.slug,
          cardSlug: resource.slug
        }
      }
    case 'deck':
      return {
        name: 'DeckDetail',
        params: {
          slug: title.value.slug,
          id: resource.id
        }
      }
    case 'hero':
      // Heroes don't have a dedicated view yet, link to collection
      return {
        name: 'Collection',
        params: {
          slug: title.value.slug
        }
      }
    default:
      return null
  }
}

const openYamlModal = async (): Promise<void> => {
  if (!title.value) return

  yamlModalOpen.value = true
  yamlLoading.value = true
  yamlError.value = null
  copied.value = false

  try {
    const response = await axios.get(`/builder/titles/${title.value.slug}/config/yaml/`)
    configYamlContent.value = response.data.yaml
  } catch (err: any) {
    yamlError.value = err.response?.data?.error || err.message || 'Failed to load YAML'
    console.error('Error fetching YAML:', err)
  } finally {
    yamlLoading.value = false
  }
}

const closeYamlModal = (): void => {
  yamlModalOpen.value = false
  configYamlContent.value = ''
  yamlError.value = null
}

const copyYaml = async (): Promise<void> => {
  try {
    await navigator.clipboard.writeText(configYamlContent.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}
</script>

<style scoped>
.title-edit-page {
  min-height: 100vh;
}
</style>

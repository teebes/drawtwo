<template>
  <div class="card-edit-page min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- Header -->
    <header class="bg-white dark:bg-gray-800 shadow">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between py-6">
          <div class="flex items-center space-x-4">
            <router-link
              :to="`/${titleSlug}/cards`"
              class="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              ← Back to Cards
            </router-link>
            <div class="h-6 border-l border-gray-300 dark:border-gray-600"></div>
            <h1 class="font-display text-2xl font-bold text-gray-900 dark:text-white">
              {{ isCreating ? 'Create New Card' : `Edit ${card?.name || 'Card'}` }}
            </h1>
          </div>
          <div class="flex items-center space-x-3">
            <span v-if="!isCreating" class="text-sm text-gray-500 dark:text-gray-400">
              v{{ card?.version }}
            </span>
            <GameButton
              v-if="!isCreating"
              variant="danger"
              size="sm"
              @click="deleteCard"
              :disabled="deleting"
            >
              {{ deleting ? 'Deleting...' : 'Delete Card' }}
            </GameButton>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
      <div v-if="loading" class="flex items-center justify-center py-12">
        <p class="text-gray-600 dark:text-gray-400">Loading card...</p>
      </div>

      <div v-else-if="error" class="text-center py-12">
        <Panel variant="error" title="Error">
          <p class="text-red-600 dark:text-red-400">{{ error }}</p>
          <router-link
            :to="`/${titleSlug}/cards`"
            class="mt-4 inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Back to Cards
          </router-link>
        </Panel>
      </div>

      <div v-else :class="isCreating ? 'max-w-6xl mx-auto' : 'grid grid-cols-1 lg:grid-cols-2 gap-8'">
        <!-- Left Column: Card Preview (hidden when creating) -->
        <div v-if="!isCreating" class="space-y-6">
          <Section title="Card Preview">
            <div class="flex justify-center">
              <CollectionCard
                v-if="card && cardForDisplay"
                :card="cardForDisplay"
                class="transform-none"
              />
            </div>
          </Section>


        </div>

        <!-- Right Column: YAML Editor -->
        <div :class="isCreating ? 'space-y-6 w-full' : 'space-y-6'">
          <Section title="YAML Definition">
            <Panel>
              <div class="space-y-4">
                <div>
                  <label for="yaml-editor" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Edit Card Definition
                  </label>
                  <textarea
                    id="yaml-editor"
                    v-model="yamlDefinition"
                    rows="20"
                    class="block w-full rounded-lg border-gray-300 font-mono text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400"
                    placeholder="Enter YAML definition..."
                    :disabled="saving"
                  />
                </div>

                                <div class="space-y-3">
                  <!-- Bump Version Checkbox (only when editing) -->
                  <div v-if="!isCreating" class="flex items-center space-x-2">
                    <input
                      id="bump-version"
                      v-model="bumpVersion"
                      type="checkbox"
                      class="rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                    />
                    <label for="bump-version" class="text-sm text-gray-700 dark:text-gray-300">
                      Create new version (v{{ (card?.version || 0) + 1 }})
                    </label>
                  </div>

                  <div class="flex items-center justify-end">
                    <div class="flex space-x-3">
                      <GameButton
                        variant="secondary"
                        @click="resetYaml"
                        :disabled="saving"
                      >
                        Reset
                      </GameButton>
                      <GameButton
                        variant="primary"
                        @click="saveCard"
                        :disabled="saving || (!hasChanges && !isCreating)"
                      >
                        {{ saving ? (isCreating ? 'Creating...' : 'Saving...') : (isCreating ? 'Create Card' : 'Save Changes') }}
                      </GameButton>
                    </div>
                  </div>
                </div>
              </div>
            </Panel>
          </Section>

          <!-- Save Success/Error Messages -->
          <div v-if="saveSuccess" class="space-y-2">
            <Panel variant="success" title="Success">
              <p v-if="lastSaveWasBump">Card updated successfully! New version: v{{ card?.version }}</p>
              <p v-else>Card updated successfully! Current version: v{{ card?.version }}</p>
            </Panel>
          </div>

          <div v-if="saveError" class="space-y-2">
            <Panel variant="error" title="Save Error">
              <p>{{ saveError }}</p>
            </Panel>
          </div>

          <div v-if="deleteError" class="space-y-2">
            <Panel variant="error" title="Delete Error">
              <p>{{ deleteError }}</p>
            </Panel>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../config/api.js'
import Section from '../components/layout/Section.vue'
import Panel from '../components/layout/Panel.vue'
import CollectionCard from '../components/game/CollectionCard.vue'
import GameButton from '../components/ui/GameButton.vue'
import type { Card } from '../types/card'

interface CardTemplate {
  id: number
  slug: string
  name: string
  description: string
  version: number
  is_latest: boolean
  card_type: 'minion' | 'spell'
  cost: number
  attack: number | null
  health: number | null
  spec: Record<string, any>
  title_slug: string
  faction_slug: string | null
  traits_with_data: Array<{
    slug: string
    name: string
    data: Record<string, any>
  }>
  yaml_definition: string
  created_at: string
  updated_at: string
}

const route = useRoute()
const router = useRouter()
const titleSlug = route.params.slug as string
const cardSlug = route.params.cardSlug as string
const isCreating = computed(() => route.name === 'CardCreate')

const card = ref<CardTemplate | null>(null)
const yamlDefinition = ref<string>('')
const originalYaml = ref<string>('')
const bumpVersion = ref<boolean>(false)
const loading = ref<boolean>(true)
const saving = ref<boolean>(false)
const error = ref<string | null>(null)
const saveError = ref<string | null>(null)
const saveSuccess = ref<boolean>(false)
const lastSaveWasBump = ref<boolean>(false)
const deleting = ref<boolean>(false)
const deleteError = ref<string | null>(null)

// Computed properties
const hasChanges = computed(() => {
  return yamlDefinition.value !== originalYaml.value
})

const cardForDisplay = computed((): Card | null => {
  if (!card.value) return null

  return {
    slug: card.value.slug,
    name: card.value.name,
    description: card.value.description,
    card_type: card.value.card_type,
    cost: card.value.cost,
    attack: card.value.attack || 0,
    health: card.value.health || 0,
    traits: card.value.traits_with_data.map(t => ({
      slug: t.slug,
      name: t.name,
      data: t.data
    })),
    faction: card.value.faction_slug
  }
})

// Methods
const fetchCard = async (): Promise<void> => {
  try {
    const response = await axios.get(`/builder/titles/${titleSlug}/cards/${cardSlug}/`)
    card.value = response.data
    yamlDefinition.value = response.data.yaml_definition
    originalYaml.value = response.data.yaml_definition
  } catch (err) {
    if (err.response?.status === 404) {
      error.value = 'Card not found'
    } else if (err.response?.status === 403) {
      error.value = 'You do not have permission to edit this card'
    } else {
      error.value = err.response?.data?.error || err.message || 'Failed to load card'
    }
    console.error('Error fetching card:', err)
  } finally {
    loading.value = false
  }
}

const saveCard = async (): Promise<void> => {
  if (!hasChanges.value && !isCreating.value) return

  try {
    saving.value = true
    saveError.value = null
    saveSuccess.value = false

    if (isCreating.value) {
      // Create new card
      const response = await axios.post(`/builder/titles/${titleSlug}/cards/`, {
        yaml_definition: yamlDefinition.value
      })

      // Redirect to edit page for the newly created card
      router.push({
        name: 'CardEdit',
        params: {
          slug: titleSlug,
          cardSlug: response.data.slug
        }
      })
    } else {
      // Update existing card
      const response = await axios.put(`/builder/titles/${titleSlug}/cards/${cardSlug}/`, {
        yaml_definition: yamlDefinition.value,
        bump_version: bumpVersion.value
      })

      // Update card data with response
      card.value = response.data
      originalYaml.value = response.data.yaml_definition
      yamlDefinition.value = response.data.yaml_definition

      // Remember if this save created a new version
      lastSaveWasBump.value = bumpVersion.value

      saveSuccess.value = true

      // Hide success message after 3 seconds
      setTimeout(() => {
        saveSuccess.value = false
      }, 3000)
    }

  } catch (err) {
    saveError.value = err.response?.data?.error || err.message || (isCreating.value ? 'Failed to create card' : 'Failed to save card')
    console.error('Error saving card:', err)
  } finally {
    saving.value = false
  }
}

const resetYaml = (): void => {
  yamlDefinition.value = originalYaml.value
  bumpVersion.value = false
  saveError.value = null
}

const deleteCard = async (): Promise<void> => {
  if (!confirm(`Are you sure you want to delete "${card.value?.name}"? This action cannot be undone.`)) {
    return
  }

  try {
    deleting.value = true
    deleteError.value = null

    await axios.delete(`/builder/titles/${titleSlug}/cards/${cardSlug}/`)

    // Redirect back to cards list after successful deletion
    router.push({
      name: 'TitleCards',
      params: { slug: titleSlug }
    })

  } catch (err) {
    deleteError.value = err.response?.data?.error || err.message || 'Failed to delete card'
    console.error('Error deleting card:', err)
  } finally {
    deleting.value = false
  }
}

// Clear success/error messages when YAML or bump version changes
watch([yamlDefinition, bumpVersion], () => {
  saveSuccess.value = false
  saveError.value = null
  deleteError.value = null
})

const initializeCard = (): void => {
  if (isCreating.value) {
    // Initialize with default values for creation
    card.value = null
    yamlDefinition.value = `name: "New Card"
description: "A new card description"
card_type: "minion"
cost: 1
attack: 1
health: 1
traits: []
`
    originalYaml.value = yamlDefinition.value
    loading.value = false
  } else {
    fetchCard()
  }
}

onMounted(() => {
  initializeCard()
})
</script>

<style scoped>
.card-edit-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
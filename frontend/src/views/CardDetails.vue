<template>
  <div v-if="!loading && card" class="h-full">
      <CardDetailContent
        :card="card"
        :title-slug="titleSlug"
        :can-edit="canEditTitle"
      >
        <template #back-button>
            <button
                type="button"
                @click="handleBack"
                class="absolute left-2 top-4 -translate-y-1/2 inline-flex items-center text-sm font-medium text-gray-600 hover:text-gray-800 dark:text-gray-700 dark:hover:text-gray-500"
            >
                ← Back
            </button>
        </template>

        <template #actions>
          <GameButton variant="secondary" size="xs" @click="openYamlModal">
            YAML
          </GameButton>
        </template>
      </CardDetailContent>

      <!-- YAML Modal -->
      <BaseModal :show="yamlModalOpen" @close="closeYamlModal">
        <div class="p-6">
          <!-- Header -->
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
              Card YAML Definition
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
            <pre class="bg-gray-900 dark:bg-gray-950 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono max-h-96 overflow-y-auto"><code>{{ yamlContent }}</code></pre>
            <p class="mt-3 text-xs text-gray-500 dark:text-gray-400">
              Copy this YAML and paste it into the ingestion tool to update this card or use as a template.
            </p>
          </div>
        </div>
      </BaseModal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../config/api'
import CardDetailContent from '../components/game/CardDetailContent.vue'
import GameButton from '../components/ui/GameButton.vue'
import BaseModal from '../components/modals/BaseModal.vue'
import { useAuthStore } from '../stores/auth'
import { useTitleStore } from '../stores/title'
import type { Card } from '../types/card'

const route = useRoute()
const router = useRouter()
const titleSlug = route.params.slug as string
const cardSlug = route.params.cardSlug as string

const card = ref<Card | null>(null)
const loading = ref<boolean>(true)

// YAML Modal state
const yamlModalOpen = ref(false)
const yamlContent = ref('')
const yamlLoading = ref(false)
const yamlError = ref<string | null>(null)
const copied = ref(false)

const authStore = useAuthStore()
const titleStore = useTitleStore()

const canEditTitle = computed(() => {
  return authStore.isAuthenticated && titleStore.currentTitle?.can_edit === true
})

// Methods
const handleBack = (): void => {
  const historyState = window.history.state as { back?: string | null } | null
  if (historyState?.back) {
    router.back()
  } else {
    router.push({ name: 'Collection', params: { slug: titleSlug } })
  }
}

const fetchCard = async (): Promise<void> => {
  try {
    const response = await axios.get(`/titles/${titleSlug}/cards/${cardSlug}/`)
    card.value = response.data
  } catch (err: any) {
    console.error('Error fetching card:', err)
  } finally {
    loading.value = false
  }
}

const openYamlModal = async (): Promise<void> => {
  yamlModalOpen.value = true
  yamlLoading.value = true
  yamlError.value = null
  copied.value = false

  try {
    const response = await axios.get(`/builder/titles/${titleSlug}/cards/${cardSlug}/yaml/`)
    yamlContent.value = response.data.yaml
  } catch (err: any) {
    yamlError.value = err.response?.data?.error || err.message || 'Failed to load YAML'
    console.error('Error fetching YAML:', err)
  } finally {
    yamlLoading.value = false
  }
}

const closeYamlModal = (): void => {
  yamlModalOpen.value = false
  yamlContent.value = ''
  yamlError.value = null
}

const copyYaml = async (): Promise<void> => {
  try {
    await navigator.clipboard.writeText(yamlContent.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

onMounted(() => {
  fetchCard()
})
</script>

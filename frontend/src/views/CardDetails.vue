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
      </CardDetailContent>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../config/api'
import CardDetailContent from '../components/game/CardDetailContent.vue'
import { useAuthStore } from '../stores/auth'
import { useTitleStore } from '../stores/title'
import type { Card } from '../types/card'

const route = useRoute()
const router = useRouter()
const titleSlug = route.params.slug as string
const cardSlug = route.params.cardSlug as string

const card = ref<Card | null>(null)
const loading = ref<boolean>(true)

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
    router.push({ name: 'TitleCards', params: { slug: titleSlug } })
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


onMounted(() => {
  fetchCard()
})
</script>

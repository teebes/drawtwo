<template>
  <div class="lobby">
    <!-- Only show content after we've loaded and determined we have multiple titles -->
    <main v-if="shouldShowTitlesList" class="flex-1 py-16">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <h2 class="text-center font-display text-3xl font-bold text-gray-900 dark:text-white mb-12">
          Choose a Title
        </h2>

        <!-- Titles Grid -->
        <div class="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          <div
            v-for="title in titles"
            :key="title.id"
            class="group cursor-pointer rounded-2xl bg-white p-8 shadow-sm transition-all hover:shadow-xl hover:-translate-y-1 dark:bg-gray-900"
            @click="navigateToTitle(title.slug)"
          >
            <div class="text-center">
              <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-r from-primary-500 to-secondary-600">
                <span class="text-2xl font-bold text-white">{{ title.name.charAt(0) }}</span>
              </div>
              <h3 class="font-display text-xl font-bold text-gray-900 dark:text-white">{{ title.name }}</h3>
              <p v-if="title.description" class="mt-2 text-gray-600 dark:text-gray-300">
                {{ title.description }}
              </p>
              <div class="mt-6">
                <div class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors group-hover:bg-primary-700">
                  Play
                  <svg class="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Error State -->
    <main v-else-if="error" class="flex-1 flex items-center justify-center min-h-[60vh]">
      <div class="text-center px-4">
        <h3 class="text-2xl font-bold text-red-600 mb-4">Error</h3>
        <p class="text-gray-600">{{ error }}</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from '../config/api'

interface TitleData {
  id: number
  slug: string
  version: number
  is_latest: boolean
  name: string
  description: string
  author: number
  author_username: string
  status: 'draft' | 'published' | 'archived'
  published_at: string | null
  created_at: string
  updated_at: string
}

const router = useRouter()
const titles = ref<TitleData[]>([])
const loading = ref<boolean>(true)
const error = ref<string | null>(null)

// Only show the titles list if we have more than 1 title
const shouldShowTitlesList = computed(() => {
  return !loading.value && !error.value && titles.value.length > 1
})

const fetchTitles = async (): Promise<void> => {
  try {
    const response = await axios.get('/titles/')
    titles.value = response.data

    // If there's only one title, redirect to it immediately
    if (titles.value.length === 1) {
      const singleTitle = titles.value[0]
      router.replace({ name: 'Title', params: { slug: singleTitle.slug } })
    }
  } catch (err) {
    console.error('Error fetching titles:', err)
    error.value = 'Failed to load titles'
  } finally {
    loading.value = false
  }
}

const navigateToTitle = (slug: string): void => {
  router.push({ name: 'Title', params: { slug } })
}

onMounted(() => {
  fetchTitles()
})
</script>

<style scoped>
.lobby {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
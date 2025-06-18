<template>
  <div class="title-page">
    <AppHeader />

    <main class="flex-1">
      <!-- Title Hero Section -->
      <section class="bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 py-16">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <!-- Loading state -->
          <div v-if="loading" class="text-center">
            <div class="animate-spin rounded-full h-16 w-16 border-4 border-white/20 border-t-white mx-auto"></div>
            <p class="mt-4 text-xl text-primary-100">Loading title...</p>
          </div>

          <!-- Error state -->
          <div v-else-if="error" class="text-center">
            <div class="mx-auto max-w-md rounded-xl bg-red-500/20 border border-red-400/30 p-8 backdrop-blur-sm">
              <h2 class="font-display text-2xl font-bold text-white mb-4">Title Not Found</h2>
              <p class="text-red-100">{{ error }}</p>
              <router-link
                to="/"
                class="mt-6 inline-flex items-center rounded-lg bg-white/20 px-4 py-2 text-sm font-medium text-white backdrop-blur-sm transition-all hover:bg-white/30"
              >
                Return Home
              </router-link>
            </div>
          </div>

          <!-- Title content -->
          <div v-else-if="title" class="text-center">
            <h1 class="font-display text-4xl font-bold text-white sm:text-5xl lg:text-6xl">
              {{ title.name }}
            </h1>
            <p class="mt-4 text-xl text-primary-100">
              Created by {{ title.author_username || "Anonymous" }}
            </p>

            <div class="mt-6 flex justify-center space-x-4">
              <span
                class="inline-flex items-center rounded-full px-4 py-2 text-sm font-medium backdrop-blur-sm"
                :class="{
                  'bg-green-500/20 text-green-100': title.status === 'published',
                  'bg-yellow-500/20 text-yellow-100': title.status === 'draft',
                  'bg-gray-500/20 text-gray-100': title.status === 'archived'
                }"
              >
                <div
                  class="mr-2 h-2 w-2 rounded-full"
                  :class="{
                    'bg-green-400': title.status === 'published',
                    'bg-yellow-400': title.status === 'draft',
                    'bg-gray-400': title.status === 'archived'
                  }"
                ></div>
                {{ title.status.charAt(0).toUpperCase() + title.status.slice(1) }}
              </span>
              <span class="inline-flex items-center rounded-full bg-white/20 px-4 py-2 text-sm font-medium text-white backdrop-blur-sm">
                Version {{ title.version }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Title Details Section -->
      <section v-if="title && !loading && !error" class="py-16 bg-gray-50 dark:bg-gray-800">
        <div class="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <!-- Description Card -->
          <div v-if="title.description" class="mb-12">
            <div class="rounded-xl bg-white p-8 shadow-sm dark:bg-gray-900">
              <h2 class="mb-4 font-display text-2xl font-bold text-gray-900 dark:text-white">
                Description
              </h2>
              <div class="prose prose-gray max-w-none dark:prose-invert">
                <p class="text-gray-700 dark:text-gray-300 leading-relaxed">
                  {{ title.description }}
                </p>
              </div>
            </div>
          </div>

          <!-- Game Details Grid -->
          <div class="grid gap-8 md:grid-cols-2">
            <!-- Metadata Card -->
            <div class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-900">
              <h3 class="mb-4 font-display text-xl font-semibold text-gray-900 dark:text-white">
                Game Details
              </h3>
              <dl class="space-y-3">
                <div class="flex justify-between">
                  <dt class="text-sm font-medium text-gray-600 dark:text-gray-400">Author</dt>
                  <dd class="text-sm text-gray-900 dark:text-white font-medium">{{ title.author_username }}</dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-sm font-medium text-gray-600 dark:text-gray-400">Version</dt>
                  <dd class="text-sm text-gray-900 dark:text-white font-medium">{{ title.version }}</dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-sm font-medium text-gray-600 dark:text-gray-400">Status</dt>
                  <dd>
                    <span
                      class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium"
                      :class="{
                        'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200': title.status === 'published',
                        'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200': title.status === 'draft',
                        'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200': title.status === 'archived'
                      }"
                    >
                      {{ title.status.charAt(0).toUpperCase() + title.status.slice(1) }}
                    </span>
                  </dd>
                </div>
                <div v-if="title.published_at" class="flex justify-between">
                  <dt class="text-sm font-medium text-gray-600 dark:text-gray-400">Published</dt>
                  <dd class="text-sm text-gray-900 dark:text-white font-medium">{{ formatDate(title.published_at) }}</dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-sm font-medium text-gray-600 dark:text-gray-400">Created</dt>
                  <dd class="text-sm text-gray-900 dark:text-white font-medium">{{ formatDate(title.created_at) }}</dd>
                </div>
              </dl>
            </div>

            <!-- Actions Card -->
            <div class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-900">
              <h3 class="mb-4 font-display text-xl font-semibold text-gray-900 dark:text-white">
                Get Started
              </h3>
              <div class="space-y-4">
                <p class="text-sm text-gray-600 dark:text-gray-400">
                  Ready to experience {{ title.name }}? Jump into the action or explore the game world.
                </p>
                <div class="space-y-3">
                  <button class="w-full rounded-lg bg-gradient-to-r from-primary-600 to-secondary-600 px-6 py-3 text-sm font-medium text-white shadow-sm transition-all hover:from-primary-700 hover:to-secondary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2">
                    Play Now
                  </button>
                  <button class="w-full rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-medium text-gray-700 shadow-sm transition-all hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">
                    View Cards
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'

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

const route = useRoute()
const title = ref<TitleData | null>(null)
const loading = ref<boolean>(true)
const error = ref<string | null>(null)

const fetchTitle = async (): Promise<void> => {
  try {
    const slug = route.params.slug as string
    const response = await fetch(`/api/builder/titles/${slug}/`)

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Title not found')
      }
      throw new Error('Failed to load title')
    }

    title.value = await response.json()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'An unknown error occurred'
    console.error('Error fetching title:', err)
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

onMounted(() => {
  fetchTitle()
})
</script>

<style scoped>
.title-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
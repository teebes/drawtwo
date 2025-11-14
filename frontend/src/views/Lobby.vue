<template>
  <div class="lobby">
    <main class="flex-1">
      <!-- Welcome Section -->
      <section class="bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 py-16">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="text-center">
            <h1 class="font-display text-4xl font-bold text-white sm:text-5xl">
              Play
            </h1>
          </div>
        </div>
      </section>

      <!-- Titles Section -->
      <section class="py-16">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="text-center font-display text-3xl font-bold text-gray-900 dark:text-white mb-12">
            Available Titles
          </h2>

          <!-- Loading State -->
          <div v-if="loading" class="text-center py-8">
            <p class="text-gray-600">Loading titles...</p>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="text-center py-8">
            <h3 class="text-2xl font-bold text-red-600 mb-4">Error</h3>
            <p class="text-gray-600">{{ error }}</p>
          </div>

          <!-- Titles Grid -->
          <div v-else-if="titles.length > 0" class="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
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
                <div class="mt-4 flex items-center justify-center space-x-4 text-sm text-gray-500">
                  <span>v{{ title.version }}</span>
                  <span>•</span>
                  <span>{{ title.author_username }}</span>
                </div>
                <div class="mt-6">
                  <div class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors group-hover:bg-primary-700">
                    Enter Title
                    <svg class="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div v-else class="text-center py-16">
            <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
              <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
              </svg>
            </div>
            <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-2">No Titles Available</h3>
            <p class="text-gray-600 dark:text-gray-300">
              No game titles are currently available. Check back later or contact an administrator.
            </p>
          </div>
        </div>
      </section>

      <!-- Quick Actions -->
      <section class="border-t border-gray-200 bg-gray-50 py-16 dark:border-gray-700 dark:bg-gray-800">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="text-center font-display text-2xl font-bold text-gray-900 dark:text-white mb-8">
            Quick Actions
          </h2>

          <div class="grid gap-6 md:grid-cols-3">
            <router-link
              to="/profile"
              class="group rounded-xl bg-white p-6 shadow-sm transition-all hover:shadow-md dark:bg-gray-900"
            >
              <div class="flex items-center space-x-4">
                <div class="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900">
                  <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                  </svg>
                </div>
                <div>
                  <h3 class="font-medium text-gray-900 dark:text-white">Profile</h3>
                  <p class="text-sm text-gray-600 dark:text-gray-300">Manage your account</p>
                </div>
              </div>
            </router-link>

            <router-link
              to="/dashboard"
              class="group rounded-xl bg-white p-6 shadow-sm transition-all hover:shadow-md dark:bg-gray-900"
            >
              <div class="flex items-center space-x-4">
                <div class="flex h-12 w-12 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900">
                  <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                  </svg>
                </div>
                <div>
                  <h3 class="font-medium text-gray-900 dark:text-white">Dashboard</h3>
                  <p class="text-sm text-gray-600 dark:text-gray-300">View your progress</p>
                </div>
              </div>
            </router-link>

            <router-link
              to="/mockup"
              class="group rounded-xl bg-white p-6 shadow-sm transition-all hover:shadow-md dark:bg-gray-900"
            >
              <div class="flex items-center space-x-4">
                <div class="flex h-12 w-12 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900">
                  <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                  </svg>
                </div>
                <div>
                  <h3 class="font-medium text-gray-900 dark:text-white">Game Modes</h3>
                  <p class="text-sm text-gray-600 dark:text-gray-300">Play matches & compete</p>
                </div>
              </div>
            </router-link>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
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

const fetchTitles = async (): Promise<void> => {
  try {
    const response = await axios.get('/titles/')
    titles.value = response.data
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
<template>
  <div class="home">
    <header class="relative border-b border-gray-200 bg-white/80 backdrop-blur-sm dark:border-gray-700 dark:bg-gray-900/80">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="flex h-16 items-center justify-between">
          <div class="flex items-center">
            <h1 class="font-display text-2xl font-bold text-gray-900 dark:text-white">
              DrawTwo
            </h1>
            <span class="ml-2 rounded-full bg-primary-100 px-2 py-1 text-xs font-medium text-primary-800 dark:bg-primary-900 dark:text-primary-200">
              TCG
            </span>
          </div>
          <nav class="flex items-center space-x-4">
            <ThemeToggle />
            <router-link
              to="/login"
              class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-all hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
            >
              Login / Sign Up
            </router-link>
          </nav>
        </div>
      </div>
    </header>

    <main class="relative">
      <!-- Hero Section -->
      <section class="relative overflow-hidden bg-gradient-to-br from-primary-900 via-purple-900 to-secondary-900 py-20 lg:py-32">
        <div class="absolute inset-0 bg-black/20"></div>
        <div class="relative mx-auto max-w-7xl px-4 text-center sm:px-6 lg:px-8">
          <h2 class="font-display text-4xl font-bold tracking-tight text-white sm:text-6xl lg:text-7xl">
            Master the Cards
          </h2>
          <p class="mx-auto mt-6 max-w-2xl text-lg leading-8 text-gray-300 sm:text-xl">
            Build your ultimate deck, duel with friends, and climb the ranks in the most strategic trading card game experience.
          </p>

          <div class="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
            <div class="rounded-2xl bg-white/10 p-8 backdrop-blur-sm transition-all hover:bg-white/20">
              <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-card-rare">
                <span class="text-xl">⚔️</span>
              </div>
              <h3 class="font-display text-xl font-semibold text-white">Strategic Combat</h3>
              <p class="mt-2 text-gray-300">
                Engage in tactical battles where every card play matters. Plan your strategy and outmaneuver opponents.
              </p>
            </div>

            <div class="rounded-2xl bg-white/10 p-8 backdrop-blur-sm transition-all hover:bg-white/20">
              <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-card-epic">
                <span class="text-xl">🃏</span>
              </div>
              <h3 class="font-display text-xl font-semibold text-white">Deck Building</h3>
              <p class="mt-2 text-gray-300">
                Craft the perfect deck from hundreds of unique cards. Discover powerful synergies and create your own meta.
              </p>
            </div>

            <div class="rounded-2xl bg-white/10 p-8 backdrop-blur-sm transition-all hover:bg-white/20">
              <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-card-legendary">
                <span class="text-xl">🏆</span>
              </div>
              <h3 class="font-display text-xl font-semibold text-white">Competitive Play</h3>
              <p class="mt-2 text-gray-300">
                Climb the ranked ladder, participate in tournaments, and prove your mastery against the best players.
              </p>
            </div>
          </div>

          <div class="mt-12">
            <router-link
              to="/login"
              class="inline-flex items-center rounded-xl bg-gradient-to-r from-primary-600 to-secondary-600 px-8 py-4 text-lg font-medium text-white shadow-xl transition-all hover:from-primary-700 hover:to-secondary-700 hover:shadow-2xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-gray-900"
            >
              Start Playing
              <svg class="ml-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
              </svg>
            </router-link>
          </div>
        </div>
      </section>

      <!-- System Status -->
      <section class="border-t border-gray-200 bg-gray-50 py-16 dark:border-gray-700 dark:bg-gray-800">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="mx-auto max-w-2xl text-center">
            <h3 class="font-display text-2xl font-bold text-gray-900 dark:text-white">System Status</h3>
            <div class="mt-6 rounded-xl bg-white p-6 shadow-sm dark:bg-gray-900">
              <div class="flex items-center justify-center">
                <div
                  class="flex items-center rounded-full px-4 py-2 text-sm font-medium"
                  :class="{
                    'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200': backendOnline,
                    'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200': !backendOnline
                  }"
                >
                  <div
                    class="mr-2 h-2 w-2 rounded-full"
                    :class="{
                      'bg-green-500': backendOnline,
                      'bg-red-500': !backendOnline
                    }"
                  ></div>
                  Game Server: {{ backendOnline ? 'Online' : 'Offline' }}
                </div>
              </div>

              <button
                @click="testBackend"
                :disabled="loading"
                class="mt-4 inline-flex items-center rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-900 transition-colors hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 dark:bg-gray-700 dark:text-gray-100 dark:hover:bg-gray-600 dark:focus:ring-offset-gray-900"
              >
                {{ loading ? 'Testing...' : 'Test Connection' }}
              </button>

              <div v-if="backendResponse" class="mt-4 rounded-lg bg-gray-100 p-3 font-mono text-sm text-gray-800 dark:bg-gray-800 dark:text-gray-200">
                {{ backendResponse }}
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import ThemeToggle from '../components/ThemeToggle.vue'

const backendOnline = ref(false)
const loading = ref(false)
const backendResponse = ref('')

const checkBackend = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/health/')
    if (response.ok) {
      backendOnline.value = true
      return await response.json()
    }
  } catch (error) {
    console.error('Backend check failed:', error)
  }
  backendOnline.value = false
  return null
}

const testBackend = async () => {
  loading.value = true
  backendResponse.value = ''

  try {
    const data = await checkBackend()
    if (data) {
      backendResponse.value = `✅ Success: ${JSON.stringify(data)}`
    } else {
      backendResponse.value = '❌ Failed to connect to game server'
    }
  } catch (error) {
    backendResponse.value = `❌ Error: ${error.message}`
  }

  loading.value = false
}

onMounted(() => {
  checkBackend()
})
</script>

<style scoped>
.home {
  min-height: 100vh;
}
</style>
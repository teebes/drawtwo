<template>
  <div class="leaderboard">
    <main class="flex-1">
      <!-- Leaderboard Header -->
      <section class="banner">
        <h1>Leaderboard</h1>
      </section>

      <!-- Leaderboard Content -->
      <section class="py-16">
        <div class="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div class="mb-6 flex items-center justify-center gap-3 text-xs font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300">
            <button
              type="button"
              class="rounded-full px-4 py-2 transition-colors"
              :class="ladderType === 'rapid' ? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900' : 'bg-gray-200 text-gray-600 hover:bg-gray-300 dark:bg-gray-800 dark:text-gray-300'"
              @click="setLadder('rapid')"
            >
              Rapid
            </button>
            <button
              type="button"
              class="rounded-full px-4 py-2 transition-colors"
              :class="ladderType === 'daily' ? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900' : 'bg-gray-200 text-gray-600 hover:bg-gray-300 dark:bg-gray-800 dark:text-gray-300'"
              @click="setLadder('daily')"
            >
              Daily
            </button>
          </div>

          <!-- Loading State -->
          <div v-if="loading" class="text-center py-12">
            <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-amber-600"></div>
            <p class="mt-4 text-gray-600 dark:text-gray-400">Loading leaderboard...</p>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="rounded-lg bg-red-50 dark:bg-red-900/20 p-6 text-center">
            <p class="text-red-800 dark:text-red-200">
              {{ error }}
            </p>
            <button
              @click="fetchLeaderboard"
              class="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Try Again
            </button>
          </div>

          <!-- Leaderboard Table -->
          <div v-else-if="players.length > 0" class="rounded-2xl bg-white shadow-sm dark:bg-gray-900 overflow-hidden">
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                  <tr>
                    <th class="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">
                      Rank
                    </th>
                    <th class="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">
                      Player
                    </th>
                    <th class="px-6 py-4 text-center text-sm font-semibold text-gray-900 dark:text-white">
                      Rating
                    </th>
                    <th class="px-6 py-4 text-center text-sm font-semibold text-gray-900 dark:text-white">
                      Wins
                    </th>
                    <th class="px-6 py-4 text-center text-sm font-semibold text-gray-900 dark:text-white">
                      Losses
                    </th>
                    <th class="px-6 py-4 text-center text-sm font-semibold text-gray-900 dark:text-white">
                      Total Games
                    </th>
                    <th class="px-6 py-4 text-center text-sm font-semibold text-gray-900 dark:text-white">
                      Win Rate
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                  <tr
                    v-for="(player, index) in players"
                    :key="player.id"
                    :class="{
                      'bg-amber-50 dark:bg-amber-900/20': index === 0,
                      'bg-gray-50 dark:bg-gray-800': index === 1,
                      'bg-orange-50 dark:bg-orange-900/20': index === 2,
                      'hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors': index > 2
                    }"
                  >
                    <!-- Rank -->
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div class="flex items-center">
                        <span v-if="index === 0" class="text-3xl">🥇</span>
                        <span v-else-if="index === 1" class="text-3xl">🥈</span>
                        <span v-else-if="index === 2" class="text-3xl">🥉</span>
                        <span v-else class="text-lg font-bold text-gray-600 dark:text-gray-400">
                          #{{ index + 1 }}
                        </span>
                      </div>
                    </td>

                    <!-- Player Name -->
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div class="flex items-center">
                        <div class="flex-shrink-0 h-10 w-10 rounded-full bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white font-bold">
                          {{ getInitials(player.display_name) }}
                        </div>
                        <div class="ml-4">
                          <div class="text-sm font-medium text-gray-900 dark:text-white">
                            {{ player.display_name }}
                            <span v-if="authStore.user && player.id === authStore.user.id" class="ml-2 inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                              You
                            </span>
                          </div>
                          <div class="text-sm text-gray-500 dark:text-gray-400" v-if="player.username">
                            @{{ player.username }}
                          </div>
                        </div>
                      </div>
                    </td>

                    <!-- Rating -->
                    <td class="px-6 py-4 whitespace-nowrap text-center">
                      <span class="inline-flex items-center rounded-full px-3 py-1 text-base font-bold"
                        :class="{
                          'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200': index < 3,
                          'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200': index >= 3
                        }"
                      >
                        {{ player.elo_rating }}
                      </span>
                    </td>

                    <!-- Wins -->
                    <td class="px-6 py-4 whitespace-nowrap text-center">
                      <span class="text-sm font-medium text-green-600 dark:text-green-400">
                        {{ player.wins }}
                      </span>
                    </td>

                    <!-- Losses -->
                    <td class="px-6 py-4 whitespace-nowrap text-center">
                      <span class="text-sm font-medium text-red-600 dark:text-red-400">
                        {{ player.losses }}
                      </span>
                    </td>

                    <!-- Total Games -->
                    <td class="px-6 py-4 whitespace-nowrap text-center">
                      <span class="text-sm font-medium text-gray-900 dark:text-white">
                        {{ player.total_games }}
                      </span>
                    </td>

                    <!-- Win Rate -->
                    <td class="px-6 py-4 whitespace-nowrap text-center">
                      <span class="text-sm font-medium text-gray-900 dark:text-white">
                        {{ calculateWinRate(player.wins, player.total_games) }}%
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Empty State -->
          <div v-else class="rounded-2xl bg-white dark:bg-gray-900 p-12 text-center shadow-sm">
            <div class="text-6xl mb-4">🎮</div>
            <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-2">
              No Rankings Yet
            </h3>
            <p class="text-gray-600 dark:text-gray-400">
              Be the first to play a PvP match and appear on the leaderboard!
            </p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useTitleStore } from '../stores/title'
import axios from '../config/api'
import type { LadderType } from '../types/game'

interface LeaderboardPlayer {
  id: number
  username?: string
  display_name: string
  avatar?: string
  elo_rating: number
  wins: number
  losses: number
  total_games: number
}

const route = useRoute()
const authStore = useAuthStore()
const titleStore = useTitleStore()
const players = ref<LeaderboardPlayer[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const ladderType = ref<LadderType>('daily')

const titleSlug = computed(() => route.params.slug as string)
const titleName = computed(() => titleStore.currentTitle?.name || titleSlug.value)
const ladderLabel = computed(() => (ladderType.value === 'daily' ? 'Daily' : 'Rapid'))

const fetchLeaderboard = async () => {
  if (!titleSlug.value) {
    error.value = 'No title specified'
    loading.value = false
    return
  }

  loading.value = true
  error.value = null

  try {
    const response = await axios.get(`/gameplay/${titleSlug.value}/leaderboard/`, {
      params: { ladder_type: ladderType.value }
    })
    players.value = response.data
  } catch (err: any) {
    console.error('Error fetching leaderboard:', err)
    error.value = err.response?.data?.error || 'Failed to load leaderboard'
  } finally {
    loading.value = false
  }
}

const getInitials = (name: string): string => {
  if (!name) return '?'
  const parts = name.split(' ')
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

const calculateWinRate = (wins: number, total: number): string => {
  if (total === 0) return '0'
  return ((wins / total) * 100).toFixed(1)
}

const setLadder = (value: LadderType): void => {
  if (ladderType.value === value) return
  ladderType.value = value
  fetchLeaderboard()
}

onMounted(() => {
  fetchLeaderboard()
})
</script>

<style scoped>
.leaderboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>

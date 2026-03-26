<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center"
    @click.self="close"
  >
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/60" @click="close" />

    <!-- Modal -->
    <div class="relative z-10 w-full max-w-sm mx-4 rounded-xl bg-white dark:bg-gray-900 shadow-2xl border border-gray-200 dark:border-gray-700 p-6">
      <!-- Header -->
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Head-to-Head
        </h2>
        <button
          class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
          @click="close"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Opponent name -->
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">
        vs <span class="font-semibold text-gray-800 dark:text-gray-200">{{ opponentName }}</span>
      </p>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-6 text-gray-500 dark:text-gray-400 text-sm">
        Loading...
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-center py-4 text-red-500 text-sm">
        {{ error }}
      </div>

      <!-- Stats -->
      <div v-else class="space-y-4">
        <!-- Record display -->
        <div class="flex justify-center items-center gap-6 text-center">
          <div>
            <div class="text-3xl font-bold text-green-500">{{ record.wins }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide mt-1">Wins</div>
          </div>
          <div class="text-2xl font-light text-gray-300 dark:text-gray-600">—</div>
          <div>
            <div class="text-3xl font-bold text-red-500">{{ record.losses }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide mt-1">Losses</div>
          </div>
          <template v-if="record.draws > 0">
            <div class="text-2xl font-light text-gray-300 dark:text-gray-600">—</div>
            <div>
              <div class="text-3xl font-bold text-gray-400">{{ record.draws }}</div>
              <div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide mt-1">Draws</div>
            </div>
          </template>
        </div>

        <!-- Total & win rate -->
        <div v-if="record.total > 0" class="border-t border-gray-100 dark:border-gray-800 pt-4 flex justify-between text-sm text-gray-500 dark:text-gray-400">
          <span>{{ record.total }} game{{ record.total !== 1 ? 's' : '' }} played</span>
          <span class="font-medium" :class="winRate >= 50 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'">
            {{ winRate }}% win rate
          </span>
        </div>

        <div v-else class="text-center text-sm text-gray-500 dark:text-gray-400 py-2">
          No completed matches yet.
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import axios from '../../config/api'

interface H2HRecord {
  wins: number
  losses: number
  draws: number
  total: number
  opponent_name: string
}

interface Props {
  isOpen: boolean
  opponentName: string
  titleSlug: string
}

const props = defineProps<Props>()
const emit = defineEmits<{ close: [] }>()

const loading = ref(false)
const error = ref<string | null>(null)
const record = ref<H2HRecord>({ wins: 0, losses: 0, draws: 0, total: 0, opponent_name: '' })

const winRate = computed(() => {
  if (record.value.total === 0) return 0
  return Math.round((record.value.wins / record.value.total) * 100)
})

const fetchRecord = async () => {
  if (!props.opponentName || !props.titleSlug) return
  loading.value = true
  error.value = null
  try {
    const response = await axios.get(`/titles/${props.titleSlug}/games/head-to-head/`, {
      params: { opponent_name: props.opponentName }
    })
    record.value = response.data
  } catch (err: any) {
    error.value = err.response?.data?.error || 'Failed to load head-to-head record'
  } finally {
    loading.value = false
  }
}

const close = () => emit('close')

watch(
  () => props.isOpen,
  (open) => {
    if (open) fetchRecord()
  }
)
</script>

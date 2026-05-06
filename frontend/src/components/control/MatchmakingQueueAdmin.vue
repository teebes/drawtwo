<template>
  <div class="space-y-6 matchmaking-queue-admin">
    <Panel title="Matchmaking Controls">
      <div class="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div class="grid gap-4 sm:grid-cols-3 flex-1">
          <div class="ui-panel-muted">
            <p class="text-sm text-gray-500 dark:text-gray-400">Queued Players</p>
            <p class="text-3xl font-bold text-primary-600 dark:text-primary-400">
              {{ summary?.queued ?? 0 }}
            </p>
          </div>
          <div class="ui-panel-muted">
            <p class="text-sm text-gray-500 dark:text-gray-400">Matched (pending)</p>
            <p class="text-3xl font-bold text-green-600 dark:text-green-400">
              {{ summary?.matched ?? 0 }}
            </p>
          </div>
          <div class="ui-panel-muted">
            <p class="text-sm text-gray-500 dark:text-gray-400">Cancelled</p>
            <p class="text-3xl font-bold text-gray-900 dark:text-gray-100">
              {{ summary?.cancelled ?? 0 }}
            </p>
          </div>
        </div>

        <div class="flex flex-col gap-4 lg:w-96">
          <div>
            <label class="ui-label mb-1">Status Filter</label>
            <select
              v-model="statusFilter"
              class="ui-select"
            >
              <option value="queued">Queued</option>
              <option value="matched">Matched</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          <div class="flex gap-3">
            <button
              class="ui-btn ui-btn-md ui-btn-secondary flex-1"
              :disabled="refreshing"
              @click="fetchQueue(true)"
            >
              <span v-if="refreshing">Refreshing...</span>
              <span v-else>Refresh</span>
            </button>

            <button
              class="ui-btn ui-btn-md ui-btn-primary flex-1"
              :disabled="isRunning || disableRunButton"
              @click="runMatchmaking()"
            >
              <span v-if="isRunning">Running...</span>
              <span v-else>Run Pass</span>
            </button>
          </div>

          <div>
            <label class="ui-label mb-1">Title Scope</label>
            <select
              v-model="selectedTitle"
              class="ui-select"
            >
              <option value="all">All Titles (queued only)</option>
              <option
                v-for="title in titleSummary"
                :key="title.title_id"
                :value="String(title.title_id)"
              >
                {{ title.title_name }} • {{ title.queued_count }} queued
              </option>
            </select>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Manual pass only runs for titles with queued players.
            </p>
          </div>
        </div>
      </div>
    </Panel>

    <Panel v-if="actionMessage" :variant="actionState === 'error' ? 'error' : 'success'">
      {{ actionMessage }}
    </Panel>

    <Panel v-if="titleSummary.length" title="Title Breakdown">
      <div class="grid gap-4 md:grid-cols-2">
        <div
          v-for="title in titleSummary"
          :key="title.title_id"
          class="ui-panel-muted flex items-center justify-between"
        >
          <div>
            <p class="text-base font-semibold text-gray-900 dark:text-white">
              {{ title.title_name }}
            </p>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              {{ title.queued_count }} queued
            </p>
          </div>
          <button
            class="ui-btn ui-btn-sm ui-btn-outline"
            :disabled="isRunning"
            @click="runMatchmaking(title.title_id)"
          >
            Run for Title
          </button>
        </div>
      </div>
    </Panel>

    <Panel title="Queue Entries">
      <div v-if="loading" class="text-center py-6 text-gray-500 dark:text-gray-400">
        Loading queue...
      </div>
      <div v-else-if="error" class="text-red-600 dark:text-red-300">
        {{ error }}
      </div>
      <div v-else>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Showing up to {{ limit }} entries • Last updated {{ formatTimestamp(lastRefreshed) }}
        </p>
        <div class="ui-table-wrap">
          <table class="ui-table">
            <thead class="bg-gray-50 dark:bg-gray-800/70">
              <tr>
                <th class="ui-table-head">Player</th>
                <th class="ui-table-head">Deck</th>
                <th class="ui-table-head">Title</th>
                <th class="ui-table-head text-right">ELO</th>
                <th class="ui-table-head text-right">Queued</th>
                <th class="ui-table-head">Match</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 dark:divide-gray-800">
              <tr v-for="entry in entries" :key="entry.id" class="bg-white dark:bg-gray-900/40">
                <td class="ui-table-cell">
                  <div class="font-medium text-gray-900 dark:text-white">{{ entry.user_display_name }}</div>
                  <div class="text-xs text-gray-500">{{ entry.user_email }}</div>
                </td>
                <td class="ui-table-cell">
                  <div class="text-gray-900 dark:text-gray-100">{{ entry.deck_name }}</div>
                  <div class="text-xs text-gray-500 dark:text-gray-400">{{ entry.hero_name }}</div>
                </td>
                <td class="ui-table-cell">
                  <div class="text-gray-900 dark:text-gray-100">{{ entry.title_name }}</div>
                  <div class="text-xs text-gray-500 dark:text-gray-400">{{ entry.title_slug }}</div>
                </td>
                <td class="ui-table-cell text-right font-semibold text-gray-900 dark:text-white">
                  {{ entry.elo_rating }}
                </td>
                <td class="ui-table-cell text-right text-sm text-gray-600 dark:text-gray-300">
                  {{ formatWait(entry.wait_seconds) }}
                </td>
                <td class="ui-table-cell">
                  <div v-if="entry.game_id" class="text-sm text-green-600 dark:text-green-400">
                    Game #{{ entry.game_id }}
                  </div>
                  <div v-else-if="entry.matched_with_entry" class="text-sm text-gray-600 dark:text-gray-300">
                    Matched with {{ entry.matched_with_entry.user_display_name || `Entry #${entry.matched_with_entry.id}` }}
                  </div>
                  <div v-else class="text-xs text-gray-500 dark:text-gray-400">
                    Waiting
                  </div>
                </td>
              </tr>
              <tr v-if="!entries.length">
                <td class="ui-table-cell text-center text-gray-500 dark:text-gray-400" colspan="6">
                  No entries for this filter.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import axios from '../../config/api'
import Panel from '../layout/Panel.vue'
import type { MatchmakingQueueEntry, MatchmakingQueueSummary } from '../../types/control'

const loading = ref(true)
const refreshing = ref(false)
const entries = ref<MatchmakingQueueEntry[]>([])
const summary = ref<MatchmakingQueueSummary | null>(null)
const lastRefreshed = ref<string | null>(null)
const error = ref<string | null>(null)
const statusFilter = ref<'queued' | 'matched' | 'cancelled'>('queued')
const selectedTitle = ref<string>('all')
const limit = ref(100)
const isRunning = ref(false)
const actionMessage = ref<string | null>(null)
const actionState = ref<'success' | 'error' | null>(null)

const titleSummary = computed(() => summary.value?.title_summary ?? [])
const disableRunButton = computed(() => !titleSummary.value.length && selectedTitle.value !== 'all')

const formatWait = (seconds: number) => {
  if (!seconds || seconds < 0) return '0s'
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const minutesLeft = minutes % 60
    return `${hours}h ${minutesLeft}m`
  }
  if (minutes) {
    return `${minutes}m ${remainingSeconds}s`
  }
  return `${remainingSeconds}s`
}

const formatTimestamp = (timestamp: string | null) => {
  if (!timestamp) return 'just now'
  const date = new Date(timestamp)
  return date.toLocaleString()
}

const fetchQueue = async (isManualRefresh = false) => {
  try {
    if (isManualRefresh) {
      refreshing.value = true
    } else {
      loading.value = true
    }
    error.value = null
    const response = await axios.get('/control/matchmaking/queue/', {
      params: {
        status: statusFilter.value,
        limit: limit.value
      }
    })

    entries.value = response.data.entries
    summary.value = response.data.summary
    lastRefreshed.value = response.data.refreshed_at
    limit.value = response.data.limit || limit.value

    const hasSelection =
      selectedTitle.value === 'all' ||
      (response.data.summary?.title_summary || []).some(
        (title: { title_id: number }) => String(title.title_id) === selectedTitle.value
      )
    if (!hasSelection) {
      selectedTitle.value = 'all'
    }
  } catch (err: any) {
    error.value = err.response?.data?.error || 'Failed to load matchmaking queue'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

const runMatchmaking = async (specificTitleId?: number | null) => {
  try {
    isRunning.value = true
    actionMessage.value = null
    actionState.value = null

    const payload: Record<string, unknown> = {}
    const titleIdToUse =
      typeof specificTitleId === 'number'
        ? specificTitleId
        : selectedTitle.value !== 'all'
          ? Number(selectedTitle.value)
          : null

    if (titleIdToUse) {
      payload.title_id = titleIdToUse
    }

    const response = await axios.post('/control/matchmaking/run/', payload)
    actionMessage.value = response.data.message || 'Matchmaking pass completed'
    actionState.value = 'success'
    await fetchQueue()
  } catch (err: any) {
    actionMessage.value = err.response?.data?.error || 'Failed to run matchmaking pass'
    actionState.value = 'error'
  } finally {
    isRunning.value = false
  }
}

watch(statusFilter, () => {
  fetchQueue()
})

onMounted(() => {
  fetchQueue()
})
</script>

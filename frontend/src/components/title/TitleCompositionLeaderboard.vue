<template>
  <div class="space-y-3">
    <p class="text-sm text-gray-500 dark:text-gray-400">Highest win rates · Ranked · All time</p>

    <p v-if="loading" class="py-6 text-sm text-gray-500 dark:text-gray-400" role="status">
      Loading top compositions…
    </p>
    <div v-else-if="error" class="ui-alert ui-alert-error" role="alert">
      <p>Unable to load the composition leaderboard.</p>
      <button type="button" class="ui-btn ui-btn-sm ui-btn-secondary mt-3" @click="fetchLeaderboard">Try again</button>
    </div>
    <template v-else-if="rows.length">
      <ol :id="listId" class="divide-y divide-gray-200 dark:divide-gray-800" aria-label="Compositions ranked by win rate">
        <li v-for="(row, index) in visibleRows" :key="row.composition.code">
          <router-link
            :to="{ name: 'CompositionDetail', params: { slug: titleSlug, code: row.composition.code }, query: filters }"
            class="group flex items-start gap-3 rounded-lg py-4 transition-colors hover:bg-primary-50/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary-500 dark:hover:bg-primary-950/20 sm:gap-4 sm:px-3"
          >
            <span class="w-6 shrink-0 text-sm tabular-nums text-gray-400">{{ index + 1 }}</span>
            <div class="min-w-0 flex-1">
              <p class="break-words text-sm font-semibold text-gray-900 group-hover:text-primary-700 dark:text-white dark:group-hover:text-primary-300 sm:text-base">
                {{ compositionLabel(row.composition) }}
              </p>
              <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {{ row.composition.total_cards }} cards
                <span v-if="row.composition.digest" class="font-mono">· {{ row.composition.digest.slice(0, 6) }}</span>
              </p>
              <p v-if="row.record.games < 20" class="mt-1 text-xs text-amber-700 dark:text-amber-400" title="Fewer than 20 recorded uses. Results may change substantially with more games.">
                Small sample
              </p>
            </div>
            <div class="shrink-0 text-right tabular-nums">
              <p class="font-bold text-emerald-700 dark:text-emerald-400">
                {{ ((row.record.win_rate || 0) * 100).toFixed(1) }}%<span class="sr-only"> win rate</span>
              </p>
              <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{{ row.record.games.toLocaleString() }} uses</p>
            </div>
          </router-link>
        </li>
      </ol>
      <button
        v-if="rows.length > 3"
        type="button"
        class="ui-btn ui-btn-md ui-btn-secondary min-h-11 w-full sm:w-auto"
        :aria-expanded="expanded"
        :aria-controls="listId"
        @click="expanded = !expanded"
      >
        {{ expanded ? 'Show top 3' : `Show top ${rows.length}` }}
        <ChevronUp v-if="expanded" class="h-4 w-4" aria-hidden="true" />
        <ChevronDown v-else class="h-4 w-4" aria-hidden="true" />
      </button>
    </template>
    <p v-else class="py-6 text-sm text-gray-500 dark:text-gray-400">
      No ranked composition results yet. Completed, tracked ranked matches will appear here.
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'
import axios from '../../config/api'
import type { CompositionBrowseResponse, CompositionBrowseRow } from '../../types/composition'
import { compositionLabel } from '../../utils/compositions'

const props = defineProps<{ titleSlug: string }>()
const filters = { game_type: 'ranked', days: 'all', ladder: 'all' }
const rows = ref<CompositionBrowseRow[]>([])
const loading = ref(true)
const error = ref(false)
const expanded = ref(false)
const listId = computed(() => `composition-leaderboard-${props.titleSlug}`)
const visibleRows = computed(() => rows.value.slice(0, expanded.value ? 20 : 3))
let controller: AbortController | null = null

const fetchLeaderboard = async () => {
  controller?.abort()
  const request = new AbortController()
  controller = request
  loading.value = true
  error.value = false
  try {
    const response = await axios.get<CompositionBrowseResponse>(
      `/gameplay/titles/${encodeURIComponent(props.titleSlug)}/compositions/`,
      { params: { ...filters, sort: 'win_rate', min_games: 1, page_size: 20 }, signal: request.signal }
    )
    if (!request.signal.aborted) rows.value = response.data.results.slice(0, 20)
  } catch {
    if (!request.signal.aborted) error.value = true
  } finally {
    if (!request.signal.aborted) loading.value = false
  }
}

watch(() => props.titleSlug, () => {
  expanded.value = false
  rows.value = []
  void fetchLeaderboard()
}, { immediate: true })

onUnmounted(() => controller?.abort())
</script>

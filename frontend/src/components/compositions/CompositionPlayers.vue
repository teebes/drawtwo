<template>
  <section class="ui-panel">
    <h2 class="ui-panel-title">Players and heroes</h2>
    <p class="ui-panel-subtitle">Players who used this card list in completed matches for the selected filters.</p>
    <p v-if="loading" class="mt-5 text-sm text-gray-500 dark:text-gray-400" role="status">Loading players…</p>
    <div v-else-if="error" class="ui-alert ui-alert-error mt-5" role="alert">
      <p>Unable to load the players who used this composition.</p>
      <button type="button" class="ui-btn ui-btn-sm ui-btn-secondary mt-3" @click="fetchPlayers">Try again</button>
    </div>
    <template v-else-if="data">
      <div v-if="data.results.length" class="ui-table-wrap mt-5">
        <table class="ui-table">
          <thead class="bg-gray-50 dark:bg-gray-800/70"><tr><th class="ui-table-head">Player</th><th class="ui-table-head">Hero</th><th class="ui-table-head text-right">Uses</th></tr></thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-800">
            <tr v-for="row in data.results" :key="`${row.player.id}:${row.hero.slug}`">
              <td class="ui-table-cell font-medium">{{ row.player.display_name }}</td>
              <td class="ui-table-cell">{{ row.hero.name }}</td>
              <td class="ui-table-cell text-right tabular-nums">{{ row.uses.toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="mt-5 text-sm text-gray-500 dark:text-gray-400">No players have recorded uses for these filters yet.</p>
      <nav v-if="data.count > data.page_size || page > 1" class="mt-5 flex items-center justify-between gap-3" aria-label="Player pages">
        <button type="button" class="ui-btn ui-btn-sm ui-btn-outline" :disabled="page <= 1" @click="page--">Previous</button>
        <span class="text-sm text-gray-500">{{ page }} / {{ Math.max(1, Math.ceil(data.count / data.page_size)) }}</span>
        <button type="button" class="ui-btn ui-btn-sm ui-btn-outline" :disabled="page * data.page_size >= data.count" @click="page++">Next</button>
      </nav>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import axios from '../../config/api'
import type { CompositionPlayersResponse } from '../../types/composition'

const props = defineProps<{ titleSlug: string; code: string }>()
const route = useRoute()
const data = ref<CompositionPlayersResponse | null>(null)
const page = ref(1)
const loading = ref(true)
const error = ref(false)
let controller: AbortController | null = null
const scope = computed(() => [props.titleSlug, props.code, route.query.game_type, route.query.days, route.query.ladder])

const fetchPlayers = async () => {
  controller?.abort()
  const request = new AbortController()
  controller = request
  loading.value = true
  error.value = false
  try {
    const response = await axios.get<CompositionPlayersResponse>(
      `/gameplay/titles/${encodeURIComponent(props.titleSlug)}/compositions/${encodeURIComponent(props.code)}/players/`,
      { params: { game_type: route.query.game_type, days: route.query.days, ladder: route.query.ladder, page: page.value, page_size: 20 }, signal: request.signal }
    )
    if (!request.signal.aborted) data.value = response.data
  } catch {
    if (!request.signal.aborted) error.value = true
  } finally {
    if (!request.signal.aborted) loading.value = false
  }
}

watch(scope, () => {
  data.value = null
  if (page.value !== 1) page.value = 1
  else void fetchPlayers()
}, { immediate: true })
watch(page, fetchPlayers)
onUnmounted(() => controller?.abort())
</script>

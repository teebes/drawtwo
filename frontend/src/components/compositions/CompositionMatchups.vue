<template>
  <section class="ui-panel !gap-0 !p-0 overflow-hidden">
    <div class="flex flex-wrap items-start justify-between gap-4 border-b border-gray-200 p-5 dark:border-gray-700">
      <div><h2 class="ui-panel-title">Composition matchups</h2><p class="ui-panel-subtitle">How this card list performs against each opposing composition.</p><p class="mt-1 text-xs text-gray-500">Win rates and records are from this composition’s perspective.</p></div>
      <label><span class="sr-only">Sort matchups</span><select v-model="sort" class="ui-select"><option value="games">Most encountered</option><option value="win_rate">Best win rate</option><option value="win_rate_asc">Worst win rate</option></select></label>
    </div>
    <p v-if="loading" class="p-8 text-center text-sm text-gray-500" role="status">Loading matchups…</p>
    <div v-else-if="error" class="p-5" role="alert"><p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p><button class="ui-btn ui-btn-sm ui-btn-outline mt-3" @click="fetchMatchups">Try again</button></div>
    <template v-else-if="data">
      <CompositionRows v-if="data.results.length" :rows="data.results" :title-slug="titleSlug" :offset="(page - 1) * data.page_size" />
      <p v-else class="p-8 text-center text-sm text-gray-500">No opposing compositions recorded for these filters yet.</p>
      <p v-if="data.unattributed_appearances" class="px-5 pb-4 text-xs text-gray-500">{{ data.unattributed_appearances }} uses have no captured opposing card list.</p>
      <nav v-if="data.count > data.page_size" class="flex items-center justify-between border-t border-gray-200 p-5 dark:border-gray-700" aria-label="Matchup pages"><button class="ui-btn ui-btn-sm ui-btn-outline" :disabled="page === 1" @click="page--">Previous</button><span class="text-sm text-gray-500">{{ page }} / {{ Math.ceil(data.count / data.page_size) }}</span><button class="ui-btn ui-btn-sm ui-btn-outline" :disabled="page * data.page_size >= data.count" @click="page++">Next</button></nav>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../../config/api'
import CompositionRows from './CompositionRows.vue'
import type { CompositionBrowseResponse } from '../../types/composition'
const props = defineProps<{ titleSlug: string; code: string }>()
const route = useRoute()
const router = useRouter()
const data = ref<CompositionBrowseResponse | null>(null)
const loading = ref(true)
const error = ref('')
const sort = computed({
  get: () => String(route.query.matchup_sort || 'games'),
  set: (value: string) => {
    const query = { ...route.query, matchup_sort: value }
    delete query.matchup_page
    router.replace({ query })
  }
})
const page = computed({
  get: () => Math.max(1, Number(route.query.matchup_page) || 1),
  set: (value: number) => router.replace({ query: { ...route.query, matchup_page: String(value) } })
})
let requestSequence = 0
const scope = computed(() => [props.titleSlug, props.code, route.query.game_type, route.query.days, route.query.ladder, sort.value])
const fetchMatchups = async () => {
  const requestId = ++requestSequence
  loading.value = true
  error.value = ''
  try {
    const response = await axios.get<CompositionBrowseResponse>(`/gameplay/titles/${encodeURIComponent(props.titleSlug)}/compositions/${encodeURIComponent(props.code)}/matchups/`, {
      params: { game_type: route.query.game_type, days: route.query.days, ladder: route.query.ladder, sort: sort.value, page: page.value, page_size: 10 }
    })
    if (requestId === requestSequence) data.value = response.data
  } catch {
    if (requestId === requestSequence) error.value = 'Unable to load composition matchups.'
  } finally {
    if (requestId === requestSequence) loading.value = false
  }
}
watch([scope, page], fetchMatchups, { immediate: true })
</script>

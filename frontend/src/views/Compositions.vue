<template>
  <div class="ui-page">
    <main class="ui-page-container">
      <router-link :to="{ name: 'Title', params: { slug: titleSlug } }" class="mb-6 inline-flex items-center gap-1 text-sm text-primary-700 dark:text-primary-400">
        <ChevronLeft class="h-4 w-4" aria-hidden="true" /> {{ titleStore.titleName }}
      </router-link>
      <header class="ui-page-header flex items-start gap-4">
        <div class="rounded-lg bg-primary-100 p-3 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300"><ChartNoAxesCombined class="h-7 w-7" aria-hidden="true" /></div>
        <div>
          <h1 class="ui-page-title">Compositions</h1>
          <p class="ui-page-subtitle">Explore card lists, compare results, and find your next build.</p>
          <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">Compare card lists, win rates, and matchups across the community.</p>
        </div>
      </header>

      <section class="ui-panel mb-6" aria-label="Filter composition statistics">
        <CompositionFilters />
        <div class="mt-5 grid grid-cols-2 gap-4 border-t border-gray-200 pt-5 dark:border-gray-700 md:grid-cols-[minmax(0,1fr)_12rem_12rem]">
          <form class="col-span-2 md:col-span-1" @submit.prevent="applySearch">
            <label class="ui-label" for="composition-search">Find a card or composition</label>
            <div class="mt-2 flex gap-2">
              <input id="composition-search" v-model="search" class="ui-input min-w-0 flex-1" type="search" maxlength="200" placeholder="Card name or exact deck code…" />
              <button class="ui-btn ui-btn-md ui-btn-secondary" type="submit" aria-label="Search compositions"><Search class="h-4 w-4" aria-hidden="true" /></button>
            </div>
          </form>
          <label><span class="ui-label">Sort by</span>
            <select class="ui-select mt-2" :value="sort" @change="update('sort', $event)">
              <option value="win_rate">Highest win rate</option><option value="win_rate_asc">Lowest win rate</option><option value="games">Most played</option>
            </select>
          </label>
          <label><span class="ui-label">Minimum uses</span>
            <select class="ui-select mt-2" :value="minimum" @change="update('min_games', $event)">
              <option value="1">Any sample size</option><option value="5">5+ uses</option><option value="20">20+ uses</option><option value="50">50+ uses</option><option value="100">100+ uses</option>
            </select>
          </label>
        </div>
      </section>

      <div v-if="loading" class="ui-panel items-center py-16 text-center" role="status"><LoaderCircle class="h-6 w-6 animate-spin text-primary-500" aria-hidden="true" /><p class="mt-3 ui-panel-subtitle">Loading composition statistics…</p></div>
      <div v-else-if="error" class="ui-alert ui-alert-error" role="alert">
        <p>{{ error }}</p>
        <div class="mt-3 flex gap-2">
          <button class="ui-btn ui-btn-sm ui-btn-secondary" @click="fetchCompositions">Try again</button>
          <button class="ui-btn ui-btn-sm ui-btn-outline" @click="resetFilters">Reset filters</button>
        </div>
      </div>
      <template v-else-if="data">
        <section v-if="data.summary" class="mb-6 grid grid-cols-3 gap-3" aria-label="Overview for selected game type and period">
          <div v-for="stat in summaryStats" :key="stat.label" class="ui-panel !p-4 sm:!p-6"><p class="text-2xl font-bold tabular-nums text-gray-900 dark:text-white sm:text-3xl">{{ stat.value.toLocaleString() }}</p><p class="mt-1 text-xs text-gray-500 dark:text-gray-400 sm:text-sm">{{ stat.label }}</p></div>
        </section>
        <section class="ui-panel !gap-0 !p-0 overflow-hidden">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 px-4 py-4 dark:border-gray-700 sm:px-6">
            <div><h2 class="ui-panel-title">{{ data.count.toLocaleString() }} {{ data.count === 1 ? 'composition' : 'compositions' }}{{ route.query.q ? ` containing “${route.query.q}”` : '' }}</h2><p class="ui-panel-subtitle">Select a card list to explore its cards and matchups.</p></div>
            <button v-if="hasFilters" class="ui-btn ui-btn-sm ui-btn-outline" @click="resetFilters">Reset filters</button>
          </div>
          <CompositionRows v-if="data.results.length" :rows="data.results" :title-slug="titleSlug" :offset="(data.page - 1) * data.page_size" />
          <div v-else class="px-6 py-16 text-center"><Layers3 class="mx-auto h-8 w-8 text-gray-400" aria-hidden="true" /><h3 class="mt-4 font-semibold text-gray-900 dark:text-white">No compositions found</h3><p class="ui-panel-subtitle">Try another card, a longer time period, or a smaller minimum sample.</p><p class="mt-2 text-sm text-gray-500">Only compositions used in completed, tracked matches appear here.</p></div>
          <nav v-if="data.count > data.page_size || data.page > 1" class="flex items-center justify-between border-t border-gray-200 px-4 py-4 dark:border-gray-700 sm:px-6" aria-label="Composition pages">
            <button class="ui-btn ui-btn-sm ui-btn-outline" :disabled="data.page <= 1" @click="setPage(data.page - 1)">Previous</button>
            <span class="text-sm text-gray-500">Page {{ data.page }} of {{ Math.max(1, Math.ceil(data.count / data.page_size)) }}</span>
            <button class="ui-btn ui-btn-sm ui-btn-outline" :disabled="data.page * data.page_size >= data.count" @click="setPage(data.page + 1)">Next</button>
          </nav>
        </section>
      </template>
      <aside class="mt-6 text-xs leading-relaxed text-gray-500 dark:text-gray-400">
        <p>Win rate = wins ÷ recorded uses; draws count as games. A mirror match contributes two uses. Samples below 20 uses are marked as small.</p>
        <p class="mt-1">Time periods use the match start date and include completed matches only. Earlier matches without composition tracking are excluded. Each composition is an exact card list, combining all heroes and card balance versions.</p>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChartNoAxesCombined, ChevronLeft, Layers3, LoaderCircle, Search } from 'lucide-vue-next'
import axios from '../config/api'
import { useTitleStore } from '../stores/title'
import CompositionFilters from '../components/compositions/CompositionFilters.vue'
import CompositionRows from '../components/compositions/CompositionRows.vue'
import type { CompositionBrowseResponse } from '../types/composition'

const route = useRoute()
const router = useRouter()
const titleStore = useTitleStore()
const titleSlug = computed(() => String(route.params.slug || ''))
const data = ref<CompositionBrowseResponse | null>(null)
const loading = ref(true)
const error = ref('')
const search = ref('')
let requestSequence = 0
const sort = computed(() => String(route.query.sort || 'win_rate'))
const minimum = computed(() => String(route.query.min_games || '1'))
const hasFilters = computed(() => Object.keys(route.query).length > 0)
const summaryStats = computed(() => [
  { label: 'Completed matches', value: data.value?.summary?.matches || 0 },
  { label: 'Recorded uses', value: data.value?.summary?.appearances || 0 },
  { label: 'Compositions in period', value: data.value?.summary?.compositions || 0 }
])
const update = (key: string, event: Event) => {
  const query = { ...route.query, [key]: (event.target as HTMLSelectElement).value }
  delete query.page
  router.push({ query })
}
const applySearch = () => {
  const query = { ...route.query }
  delete query.page
  if (search.value.trim()) query.q = search.value.trim()
  else delete query.q
  router.push({ query })
}
const setPage = (page: number) => router.push({ query: { ...route.query, page: String(page) } })
const resetFilters = () => router.push({ query: {} })
const fetchCompositions = async () => {
  const requestId = ++requestSequence
  loading.value = true
  error.value = ''
  try {
    const response = await axios.get<CompositionBrowseResponse>(`/gameplay/titles/${encodeURIComponent(titleSlug.value)}/compositions/`, { params: route.query })
    if (requestId === requestSequence) data.value = response.data
  } catch {
    if (requestId === requestSequence) error.value = 'Unable to load composition statistics. Try again or reset the filters.'
  } finally {
    if (requestId === requestSequence) loading.value = false
  }
}
watch(() => route.query.q, value => { search.value = String(value || '') }, { immediate: true })
watch(() => [titleSlug.value, route.query], fetchCompositions, { immediate: true })
</script>

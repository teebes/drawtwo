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
          <p class="ui-page-subtitle">Track your builds and discover what works.</p>
        </div>
      </header>

      <div class="ui-tabs-shell mb-6">
        <nav class="ui-tabs" aria-label="Composition scope">
          <button v-if="authStore.isAuthenticated" type="button" :class="['ui-tab flex-1 sm:flex-none', personal ? 'ui-tab-active' : 'ui-tab-inactive']" :aria-pressed="personal" @click="setScope('mine')">Your compositions</button>
          <router-link v-else :to="{ name: 'Login', query: { redirect: ownCompositionsPath } }" class="ui-tab ui-tab-inactive flex-1 sm:flex-none">Your compositions</router-link>
          <button type="button" :class="['ui-tab flex-1 sm:flex-none', !personal ? 'ui-tab-active' : 'ui-tab-inactive']" :aria-pressed="!personal" @click="setScope('all')">All compositions</button>
        </nav>
      </div>

      <p class="mb-4 text-sm text-gray-600 dark:text-gray-300">{{ personal ? 'Your results with the compositions you’ve played. Rankings and filters use your games only.' : 'Community results across all players. Compare compositions and explore their matchups.' }}</p>
      <section v-if="!loading && !error && data?.summary" class="mb-6 grid grid-cols-3 gap-3" :aria-label="personal ? 'Your performance for the selected game type and period' : 'Community overview for the selected game type and period'">
        <div v-for="stat in summaryStats" :key="stat.label" class="ui-panel !p-3 sm:!p-6">
          <p class="text-2xl font-bold tabular-nums text-gray-900 dark:text-white sm:text-3xl">{{ stat.value }}</p>
          <p class="mt-1 text-xs text-gray-500 dark:text-gray-400 sm:text-sm">{{ stat.label }}</p>
          <p v-if="stat.detail" class="mt-1 text-[10px] tabular-nums sm:text-xs text-gray-500 dark:text-gray-400">{{ stat.detail }}</p>
        </div>
      </section>

      <section class="ui-panel mb-6 !p-4 sm:!p-6" aria-label="Filter composition statistics">
        <details>
          <summary class="cursor-pointer text-sm font-semibold text-gray-800 dark:text-gray-200">
            Filters and sorting
            <span class="mt-1 block pl-4 text-xs font-normal text-gray-500 dark:text-gray-400">{{ filterDescription }}</span>
          </summary>
          <div class="mt-5">
            <CompositionFilters />
            <div class="mt-5 grid grid-cols-2 gap-4 border-t border-gray-200 pt-5 dark:border-gray-700 md:grid-cols-[minmax(0,1fr)_12rem_12rem]">
              <form class="col-span-2 md:col-span-1" @submit.prevent="applySearch">
                <label class="ui-label" for="composition-search">Find a card or composition</label>
                <div class="mt-2 flex gap-2">
                  <input id="composition-search" v-model="search" class="ui-input min-w-0 flex-1" type="search" maxlength="200" placeholder="Composition name, card, or deck code…" />
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
          </div>
        </details>
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
        <section class="ui-panel !gap-0 !p-0 overflow-hidden">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 px-4 py-4 dark:border-gray-700 sm:px-6">
            <div><h2 class="ui-panel-title">{{ personal ? 'Your compositions' : 'All compositions' }} <span class="ml-1 text-base font-normal text-gray-500">({{ data.count.toLocaleString() }})</span></h2><p class="ui-panel-subtitle">{{ personal ? 'Your win rates and records for each card list.' : 'Community win rates and records for each card list.' }}{{ route.query.q ? ` Matching “${route.query.q}”.` : '' }}</p></div>
            <button v-if="hasFilters" class="ui-btn ui-btn-sm ui-btn-outline" @click="resetFilters">Reset filters</button>
          </div>
          <CompositionRows v-if="data.results.length" :rows="data.results" :title-slug="titleSlug" :offset="(data.page - 1) * data.page_size" :personal="personal" />
          <div v-else class="px-6 py-16 text-center">
            <Layers3 class="mx-auto h-8 w-8 text-gray-400" aria-hidden="true" />
            <h3 class="mt-4 font-semibold text-gray-900 dark:text-white">{{ personal ? 'No compositions played with these filters' : 'No compositions found' }}</h3>
            <p class="ui-panel-subtitle">Try another game type, a longer time period, or a smaller minimum sample.</p>
            <p class="mt-2 text-sm text-gray-500">Only compositions used in completed, tracked matches appear here.</p>
            <button v-if="personal" class="ui-btn ui-btn-md ui-btn-secondary mt-5" @click="setScope('all')">Explore all compositions</button>
          </div>
          <nav v-if="data.count > data.page_size || data.page > 1" class="flex items-center justify-between border-t border-gray-200 px-4 py-4 dark:border-gray-700 sm:px-6" aria-label="Composition pages">
            <button class="ui-btn ui-btn-sm ui-btn-outline" :disabled="data.page <= 1" @click="setPage(data.page - 1)">Previous</button>
            <span class="text-sm text-gray-500">Page {{ data.page }} of {{ Math.max(1, Math.ceil(data.count / data.page_size)) }}</span>
            <button class="ui-btn ui-btn-sm ui-btn-outline" :disabled="data.page * data.page_size >= data.count" @click="setPage(data.page + 1)">Next</button>
          </nav>
        </section>
      </template>
      <aside class="mt-6 text-xs leading-relaxed text-gray-500 dark:text-gray-400">
        <p>Win rate = wins ÷ recorded uses; draws count as games. Community totals count both sides of mirror matches. Samples below 20 uses are marked as small.</p>
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
import { useAuthStore } from '../stores/auth'
import CompositionFilters from '../components/compositions/CompositionFilters.vue'
import CompositionRows from '../components/compositions/CompositionRows.vue'
import type { CompositionBrowseResponse } from '../types/composition'

const route = useRoute()
const router = useRouter()
const titleStore = useTitleStore()
const authStore = useAuthStore()
const titleSlug = computed(() => String(route.params.slug || ''))
const data = ref<CompositionBrowseResponse | null>(null)
const loading = ref(true)
const error = ref('')
const search = ref('')
let requestSequence = 0
const sort = computed(() => String(route.query.sort || 'win_rate'))
const minimum = computed(() => String(route.query.min_games || '1'))
const personal = computed(() => authStore.isAuthenticated && route.query.scope !== 'all')
const ownCompositionsPath = computed(() => {
  const query = { ...route.query }
  delete query.page
  query.scope = 'mine'
  return router.resolve({ name: 'Compositions', params: { slug: titleSlug.value }, query }).fullPath
})
const hasFilters = computed(() => Object.keys(route.query).some(key => key !== 'scope'))
const filterDescription = computed(() => [
  route.query.game_type === 'friendly' ? 'Friendly' : 'Ranked',
  !route.query.days || route.query.days === 'all' ? 'All time' : `Last ${route.query.days} days`,
  route.query.game_type === 'friendly' ? '' : route.query.ladder === 'daily' ? 'Daily' : route.query.ladder === 'rapid' ? 'Rapid' : 'All ladders',
  sort.value === 'games' ? 'Most played' : sort.value === 'win_rate_asc' ? 'Lowest win rate' : 'Highest win rate',
  minimum.value !== '1' ? `${minimum.value}+ uses` : '',
  route.query.q ? `“${route.query.q}”` : ''
].filter(Boolean).join(' · '))
const summaryStats = computed<Array<{ label: string; value: string; detail?: string }>>(() => {
  const summary = data.value?.summary
  const record = summary?.record
  return personal.value ? [
    { label: 'Your win rate', value: `${((record?.win_rate || 0) * 100).toFixed(1)}%`, detail: `${record?.wins || 0}W · ${record?.losses || 0}L · ${record?.draws || 0}D` },
    { label: 'Games played', value: (summary?.appearances || 0).toLocaleString() },
    { label: 'Compositions played', value: (summary?.compositions || 0).toLocaleString() }
  ] : [
    { label: 'Completed matches', value: (summary?.matches || 0).toLocaleString() },
    { label: 'Recorded uses', value: (summary?.appearances || 0).toLocaleString() },
    { label: 'Compositions in period', value: (summary?.compositions || 0).toLocaleString() }
  ]
})
const setScope = (scope: 'mine' | 'all') => {
  const query = { ...route.query }
  delete query.page
  query.scope = scope
  router.push({ query })
}
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
const resetFilters = () => router.push({ query: { scope: personal.value ? 'mine' : 'all' } })
const fetchCompositions = async () => {
  const requestId = ++requestSequence
  loading.value = true
  error.value = ''
  try {
    const response = await axios.get<CompositionBrowseResponse>(`/gameplay/titles/${encodeURIComponent(titleSlug.value)}/compositions/`, { params: { ...route.query, scope: personal.value ? 'mine' : 'all' } })
    if (requestId === requestSequence) data.value = response.data
  } catch {
    if (requestId === requestSequence) error.value = 'Unable to load composition statistics. Try again or reset the filters.'
  } finally {
    if (requestId === requestSequence) loading.value = false
  }
}
watch(() => route.query.q, value => { search.value = String(value || '') }, { immediate: true })
watch(() => [titleSlug.value, route.query, authStore.user?.id, authStore.isAuthenticated], fetchCompositions, { immediate: true })
</script>

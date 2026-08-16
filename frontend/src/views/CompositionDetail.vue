<template>
  <div class="ui-page">
    <main class="ui-page-container ui-page-container-narrow">
      <router-link
        :to="{ name: 'Title', params: { slug: titleSlug } }"
        class="mb-6 inline-flex items-center gap-1 text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
      >
        <ChevronLeft class="h-4 w-4" aria-hidden="true" />
        Back to {{ titleName }}
      </router-link>

      <header class="ui-page-header">
        <div class="flex items-start gap-3">
          <div class="rounded-lg bg-primary-100 p-2 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300">
            <Layers3 class="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <h1 class="ui-page-title">Deck composition</h1>
            <p class="ui-page-subtitle">
              Results for this exact card list, independent of the hero used to play it.
            </p>
          </div>
        </div>
      </header>

      <div class="space-y-6">
        <section class="ui-panel">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 class="ui-panel-title">Deck code</h2>
              <p class="ui-panel-subtitle">Paste this one-line code into another message or URL to share the composition.</p>
            </div>
            <div v-if="composition" class="flex flex-wrap items-center gap-2">
              <span class="ui-status-badge ui-status-neutral">
                {{ composition.total_cards }} {{ composition.total_cards === 1 ? 'card' : 'cards' }}
              </span>
              <button
                v-if="authStore.isAuthenticated"
                type="button"
                :class="['ui-btn ui-btn-sm', composition.is_favorite ? 'ui-btn-secondary' : 'ui-btn-outline']"
                :disabled="favoriteUpdating"
                :aria-pressed="composition.is_favorite === true"
                @click="toggleFavorite"
              >
                <Star :class="['h-4 w-4', composition.is_favorite ? 'fill-current' : '']" aria-hidden="true" />
                {{ composition.is_favorite ? 'Favorited' : 'Favorite' }}
              </button>
              <router-link
                v-else
                :to="{ name: 'Login', query: { redirect: route.fullPath } }"
                class="ui-btn ui-btn-sm ui-btn-outline"
              >
                <Star class="h-4 w-4" aria-hidden="true" />
                Favorite
              </router-link>
            </div>
          </div>

          <div class="mt-4 flex min-w-0 flex-col gap-2 sm:flex-row">
            <input
              class="ui-input min-w-0 flex-1 font-mono"
              type="text"
              readonly
              :value="displayCode"
              aria-label="Deck composition code"
              @focus="selectInput"
            />
            <button
              type="button"
              class="ui-btn ui-btn-md ui-btn-secondary flex-none"
              @click="copyCode"
            >
              <Check v-if="copied" class="h-4 w-4" aria-hidden="true" />
              <Copy v-else class="h-4 w-4" aria-hidden="true" />
              {{ copied ? 'Copied' : 'Copy code' }}
            </button>
          </div>
        </section>

        <div class="ui-tabs-shell !mb-0">
          <div class="ui-tabs-scroll">
            <nav class="ui-tabs" aria-label="Game type">
              <button
                v-for="option in gameTypeOptions"
                :key="option.value"
                type="button"
                :class="['ui-tab', gameType === option.value ? 'ui-tab-active' : 'ui-tab-inactive']"
                :aria-pressed="gameType === option.value"
                @click="setGameType(option.value)"
              >
                {{ option.label }}
              </button>
            </nav>
          </div>
        </div>

        <div v-if="loading" class="ui-panel items-center py-12 text-center" aria-live="polite">
          <LoaderCircle class="mb-3 h-6 w-6 animate-spin text-primary-600 dark:text-primary-400" aria-hidden="true" />
          <p class="text-sm text-gray-600 dark:text-gray-300">Loading composition results…</p>
        </div>

        <div v-else-if="error" class="ui-alert ui-alert-error">
          <p class="font-medium">Unable to load this composition</p>
          <p class="mt-1">{{ error }}</p>
          <button type="button" class="ui-btn ui-btn-sm ui-btn-secondary mt-4" @click="fetchStats">
            Try again
          </button>
        </div>

        <template v-else-if="stats">
          <div v-if="stats.attribution?.legacy_games_excluded" class="ui-alert ui-alert-info">
            Exact composition results begin when composition tracking was introduced. Earlier games remain in player-level records but are not attributed to this card list.
          </div>

          <section class="grid gap-6 sm:grid-cols-2">
            <div class="ui-panel">
              <p class="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Global record</p>
              <template v-if="stats.global.games > 0">
                <p class="ui-stat-value mt-3">{{ formatWinRate(stats.global) }}</p>
                <p class="ui-stat-label">win rate across {{ appearanceCountLabel(stats.global.games) }}</p>
                <p class="mt-4 text-sm font-medium text-gray-700 dark:text-gray-200">
                  {{ recordLabel(stats.global) }}
                </p>
              </template>
              <div v-else class="mt-4">
                <p class="text-lg font-semibold text-gray-900 dark:text-white">No {{ gameType }} games yet</p>
                <p class="ui-panel-subtitle">Results will appear after this composition completes an eligible game.</p>
              </div>
            </div>

            <div class="ui-panel">
              <p class="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Your record</p>
              <template v-if="stats.player && stats.player.games > 0">
                <p class="ui-stat-value mt-3">{{ formatWinRate(stats.player) }}</p>
                <p class="ui-stat-label">win rate across {{ gameCountLabel(stats.player.games) }}</p>
                <p class="mt-4 text-sm font-medium text-gray-700 dark:text-gray-200">
                  {{ recordLabel(stats.player) }}
                </p>
              </template>
              <div v-else-if="authStore.isAuthenticated" class="mt-4">
                <p class="text-lg font-semibold text-gray-900 dark:text-white">No personal games yet</p>
                <p class="ui-panel-subtitle">Your results will appear once you play this composition.</p>
              </div>
              <div v-else class="mt-4">
                <p class="text-lg font-semibold text-gray-900 dark:text-white">See your record</p>
                <p class="ui-panel-subtitle">Sign in to compare your results with the global record.</p>
                <router-link
                  :to="{ name: 'Login', query: { redirect: route.fullPath } }"
                  class="ui-btn ui-btn-sm ui-btn-primary mt-4"
                >
                  Sign in
                </router-link>
              </div>
            </div>
          </section>

          <section class="ui-panel">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 class="ui-panel-title">Hero matchups</h2>
                <p class="ui-panel-subtitle">Break down this card list by the hero that used it and the opposing hero.</p>
              </div>
              <button
                type="button"
                :class="['ui-btn ui-btn-sm', showHeroBreakdown ? 'ui-btn-secondary' : 'ui-btn-outline']"
                @click="setHeroBreakdown(!showHeroBreakdown)"
              >
                {{ showHeroBreakdown ? 'Hide breakdown' : 'Show breakdown' }}
              </button>
            </div>

            <div v-if="showHeroBreakdown" class="mt-5">
              <div v-if="stats.hero_matchups.length" class="ui-table-wrap">
                <table class="ui-table">
                  <thead class="bg-gray-50 dark:bg-gray-800/70">
                    <tr>
                      <th class="ui-table-head">Hero matchup</th>
                      <th class="ui-table-head">Global</th>
                      <th class="ui-table-head">Your record</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-800 dark:bg-gray-900/40">
                    <tr v-for="matchup in stats.hero_matchups" :key="`${matchup.hero.slug}:${matchup.opponent_hero.slug}`">
                      <td class="ui-table-cell">
                        <p class="font-medium text-gray-900 dark:text-white">{{ matchup.hero.name }}</p>
                        <p class="text-sm text-gray-500 dark:text-gray-400">vs. {{ matchup.opponent_hero.name }}</p>
                      </td>
                      <td class="ui-table-cell whitespace-nowrap text-sm text-gray-700 dark:text-gray-200">
                        <template v-if="matchup.global.games">
                          <span class="font-semibold">{{ formatWinRate(matchup.global) }}</span>
                          <span class="block text-xs text-gray-500 dark:text-gray-400">{{ recordLabel(matchup.global) }}</span>
                        </template>
                        <span v-else class="text-gray-400">—</span>
                      </td>
                      <td class="ui-table-cell whitespace-nowrap text-sm text-gray-700 dark:text-gray-200">
                        <template v-if="matchup.player && matchup.player.games">
                          <span class="font-semibold">{{ formatWinRate(matchup.player) }}</span>
                          <span class="block text-xs text-gray-500 dark:text-gray-400">{{ recordLabel(matchup.player) }}</span>
                        </template>
                        <span v-else class="text-gray-400">—</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p v-else class="text-sm text-gray-500 dark:text-gray-400">
                No hero matchup data is available for these {{ gameType }} results yet.
              </p>
            </div>
            <p v-else class="mt-5 text-sm text-gray-500 dark:text-gray-400">
              The headline result combines games played with every hero.
            </p>
          </section>

          <section class="ui-panel">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 class="ui-panel-title">Cards</h2>
                <p class="ui-panel-subtitle">The hero is intentionally not part of this composition.</p>
              </div>
              <span class="ui-status-badge ui-status-info">Hero-independent</span>
            </div>

            <div v-if="compositionCards.length" class="mt-5 grid gap-2 sm:grid-cols-2">
              <div
                v-for="card in compositionCards"
                :key="card.slug"
                class="ui-panel-muted flex items-center justify-between gap-3 !p-3"
              >
                <div class="min-w-0">
                  <p class="truncate font-medium text-gray-900 dark:text-white">{{ card.name || humanizeSlug(card.slug) }}</p>
                  <p class="truncate font-mono text-xs text-gray-500 dark:text-gray-400">{{ card.slug }}</p>
                </div>
                <span class="flex-none rounded-full bg-gray-200 px-2.5 py-1 text-sm font-bold text-gray-700 dark:bg-gray-700 dark:text-gray-200">
                  {{ card.count }}×
                </span>
              </div>
            </div>
            <p v-else class="mt-5 text-sm text-gray-500 dark:text-gray-400">This composition has no cards.</p>
          </section>
        </template>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check, ChevronLeft, Copy, Layers3, LoaderCircle, Star } from 'lucide-vue-next'
import axios from '../config/api'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notifications'
import { useTitleStore } from '../stores/title'
import type {
  CompositionCard,
  CompositionGameType,
  CompositionRecord,
  CompositionStatsResponse
} from '../types/composition'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const notificationStore = useNotificationStore()
const titleStore = useTitleStore()

const stats = ref<CompositionStatsResponse | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const copied = ref(false)
const favoriteUpdating = ref(false)
let copyResetTimer: ReturnType<typeof setTimeout> | null = null
let requestSequence = 0

const gameTypeOptions: Array<{ value: CompositionGameType; label: string }> = [
  { value: 'ranked', label: 'Ranked' },
  { value: 'friendly', label: 'Friendly' }
]

const titleSlug = computed(() => String(route.params.slug || ''))
const titleName = computed(() => titleStore.titleName || titleSlug.value)
const routeCode = computed(() => String(route.params.code || ''))
const gameType = computed<CompositionGameType>(() => route.query.game_type === 'friendly' ? 'friendly' : 'ranked')
const showHeroBreakdown = computed(() => route.query.breakdown === 'hero')
const composition = computed(() => stats.value?.composition || null)
const displayCode = computed(() => composition.value?.code || routeCode.value)
const compositionCards = computed<CompositionCard[]>(() => {
  return [...(composition.value?.cards || [])].sort((a, b) => {
    return (a.name || a.slug).localeCompare(b.name || b.slug)
  })
})

const selectInput = (event: FocusEvent): void => {
  ;(event.target as HTMLInputElement).select()
}

const copyCode = async (): Promise<void> => {
  if (!displayCode.value) return

  try {
    await navigator.clipboard.writeText(displayCode.value)
    copied.value = true
    if (copyResetTimer) clearTimeout(copyResetTimer)
    copyResetTimer = setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    copied.value = false
    notificationStore.warning('Copy failed. Select the deck code and copy it manually.')
  }
}

const toggleFavorite = async (): Promise<void> => {
  if (!composition.value || favoriteUpdating.value) return

  const shouldFavorite = !composition.value.is_favorite
  favoriteUpdating.value = true
  const url = `/collection/titles/${encodeURIComponent(titleSlug.value)}/compositions/${encodeURIComponent(routeCode.value)}/favorite/`

  try {
    const response = shouldFavorite
      ? await axios.put(url)
      : await axios.delete(url)
    composition.value.is_favorite = response.data.is_favorite === true
    notificationStore.success(
      composition.value.is_favorite
        ? 'Composition added to your favorites.'
        : 'Composition removed from your favorites.'
    )
  } catch (err: any) {
    notificationStore.handleApiError(err, 'Unable to update this favorite.')
  } finally {
    favoriteUpdating.value = false
  }
}

const setGameType = (value: CompositionGameType): void => {
  const query = { ...route.query }
  if (value === 'ranked') {
    delete query.game_type
  } else {
    query.game_type = value
  }
  router.replace({ query })
}

const setHeroBreakdown = (enabled: boolean): void => {
  const query = { ...route.query }
  if (enabled) {
    query.breakdown = 'hero'
  } else {
    delete query.breakdown
  }
  router.replace({ query })
}

const normalizeRecord = (record: Partial<CompositionRecord> | null | undefined): CompositionRecord => {
  const wins = Number(record?.wins || 0)
  const losses = Number(record?.losses || 0)
  const draws = Number(record?.draws || 0)
  const games = Number(record?.games ?? wins + losses + draws)
  const suppliedRate = record?.win_rate

  return {
    wins,
    losses,
    draws,
    games,
    win_rate: suppliedRate === null || suppliedRate === undefined ? null : Number(suppliedRate)
  }
}

const normalizeResponse = (payload: CompositionStatsResponse): CompositionStatsResponse => {
  return {
    ...payload,
    composition: {
      ...payload.composition,
      total_cards: Number(payload.composition.total_cards || 0),
      cards: (payload.composition.cards || []).map(card => ({
        ...card,
        count: Number(card.count || 0)
      }))
    },
    global: normalizeRecord(payload.global),
    player: payload.player ? normalizeRecord(payload.player) : null,
    hero_matchups: (payload.hero_matchups || []).map(matchup => ({
      ...matchup,
      global: normalizeRecord(matchup.global),
      player: matchup.player ? normalizeRecord(matchup.player) : null
    }))
  }
}

const fetchStats = async (): Promise<void> => {
  if (!titleSlug.value || !routeCode.value) {
    stats.value = null
    error.value = 'The composition URL is incomplete.'
    loading.value = false
    return
  }

  const requestId = ++requestSequence
  stats.value = null
  loading.value = true
  error.value = null

  try {
    const response = await axios.get<CompositionStatsResponse>(
      `/gameplay/titles/${encodeURIComponent(titleSlug.value)}/compositions/${encodeURIComponent(routeCode.value)}/stats/`,
      {
        params: {
          game_type: gameType.value,
          ...(showHeroBreakdown.value ? { breakdown: 'hero' } : {})
        }
      }
    )

    if (requestId !== requestSequence) return
    stats.value = normalizeResponse(response.data)
  } catch (err: any) {
    if (requestId !== requestSequence) return
    const apiMessage = err.response?.data?.detail || err.response?.data?.error || err.response?.data?.message
    error.value = apiMessage || (err.response?.status === 404
      ? 'The deck code is invalid or has not been recorded for this title.'
      : 'Composition results are temporarily unavailable.')
  } finally {
    if (requestId === requestSequence) {
      loading.value = false
    }
  }
}

const formatWinRate = (record: CompositionRecord): string => {
  const rate = record.win_rate === null
    ? (record.games > 0 ? (record.wins / record.games) * 100 : 0)
    : record.win_rate * 100
  return `${rate.toFixed(1)}%`
}

const recordLabel = (record: CompositionRecord): string => {
  const drawSuffix = record.draws > 0 ? ` · ${record.draws}D` : ''
  return `${record.wins}W · ${record.losses}L${drawSuffix}`
}

const gameCountLabel = (games: number): string => `${games} ${games === 1 ? 'game' : 'games'}`
const appearanceCountLabel = (games: number): string => `${games} recorded ${games === 1 ? 'use' : 'uses'}`

const humanizeSlug = (slug: string): string => {
  return slug
    .split('-')
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

watch(
  [titleSlug, routeCode, gameType, showHeroBreakdown],
  fetchStats,
  { immediate: true }
)
</script>

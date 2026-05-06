<template>
  <div class="ui-page">
    <main class="ui-page-container">
      <header class="ui-page-header-row">
        <div>
          <router-link
            :to="{ name: 'GameConfig', params: { slug } }"
            class="mb-3 inline-flex items-center gap-2 text-sm font-medium text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <ArrowLeft class="h-4 w-4" aria-hidden="true" />
            Game Config
          </router-link>
          <h1 class="ui-page-title">Heroes & Cards</h1>
          <p class="ui-page-meta">{{ pageTitle }}</p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <router-link
            :to="{ name: 'TitleEdit', params: { slug } }"
            class="ui-btn ui-btn-md ui-btn-secondary"
          >
            <FileCode2 class="h-4 w-4" aria-hidden="true" />
            Edit YAML
          </router-link>
          <router-link
            :to="{ name: 'CardCreate', params: { slug } }"
            class="ui-btn ui-btn-md ui-btn-primary"
          >
            <Plus class="h-4 w-4" aria-hidden="true" />
            New Card
          </router-link>
        </div>
      </header>

      <div v-if="loading" class="ui-panel min-h-64 items-center justify-center">
        <Loader2 class="h-6 w-6 animate-spin text-primary-600" aria-hidden="true" />
      </div>

      <div v-else-if="error" class="ui-alert ui-alert-error">
        {{ error }}
      </div>

      <div v-else class="space-y-8">
        <section class="grid gap-4 md:grid-cols-4">
          <div class="ui-panel-muted">
            <p class="text-sm text-gray-500 dark:text-gray-400">Heroes</p>
            <p class="ui-stat-value">{{ heroes.length }}</p>
          </div>
          <div class="ui-panel-muted">
            <p class="text-sm text-gray-500 dark:text-gray-400">Cards</p>
            <p class="ui-stat-value">{{ cards.length }}</p>
          </div>
          <div class="ui-panel-muted">
            <p class="text-sm text-gray-500 dark:text-gray-400">Collectible</p>
            <p class="ui-stat-value">{{ collectibleCardCount }}</p>
          </div>
          <div class="ui-panel-muted">
            <p class="text-sm text-gray-500 dark:text-gray-400">Hero scoped</p>
            <p class="ui-stat-value">{{ heroScopedCardCount }}</p>
          </div>
        </section>

        <div class="ui-tabs-shell">
          <div class="ui-tabs-scroll">
            <nav class="ui-tabs" aria-label="Content configuration sections">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                type="button"
                :class="['ui-tab', activeTab === tab.id ? 'ui-tab-active' : 'ui-tab-inactive']"
                @click="activeTab = tab.id"
              >
                {{ tab.name }}
              </button>
            </nav>
          </div>
        </div>

        <section v-if="activeTab === 'heroes'" class="ui-panel">
          <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 class="ui-panel-title">Heroes</h2>
              <p class="ui-panel-subtitle">Latest hero templates for this title.</p>
            </div>
            <router-link
              :to="{ name: 'TitleEdit', params: { slug } }"
              class="ui-btn ui-btn-sm ui-btn-secondary self-start sm:self-auto"
            >
              <FileCode2 class="h-4 w-4" aria-hidden="true" />
              Edit Heroes
            </router-link>
          </div>

          <div v-if="heroes.length === 0" class="ui-panel-muted text-sm text-gray-500 dark:text-gray-400">
            No heroes have been created for this title.
          </div>

          <div v-else class="ui-table-wrap">
            <table class="ui-table">
              <thead class="bg-gray-50 dark:bg-gray-800/70">
                <tr>
                  <th class="ui-table-head">Hero</th>
                  <th class="ui-table-head">Health</th>
                  <th class="ui-table-head">Power</th>
                  <th class="ui-table-head">Faction</th>
                  <th class="ui-table-head text-right">Scoped cards</th>
                  <th class="ui-table-head text-right">Version</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-800 dark:bg-gray-900/40">
                <tr v-for="hero in heroes" :key="hero.id">
                  <td class="ui-table-cell">
                    <div class="flex items-center gap-3">
                      <div class="flex h-10 w-10 flex-none items-center justify-center rounded-lg bg-gray-100 text-sm font-semibold text-gray-700 dark:bg-gray-800 dark:text-gray-200">
                        {{ hero.name.charAt(0).toUpperCase() }}
                      </div>
                      <div>
                        <div class="font-medium text-gray-900 dark:text-white">{{ hero.name }}</div>
                        <div class="text-xs text-gray-500 dark:text-gray-400">{{ hero.slug }}</div>
                      </div>
                    </div>
                  </td>
                  <td class="ui-table-cell font-semibold text-gray-900 dark:text-white">
                    {{ hero.health }}
                  </td>
                  <td class="ui-table-cell">
                    <div class="text-sm text-gray-900 dark:text-white">{{ heroPowerName(hero) }}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">
                      {{ heroPowerActionCount(hero) }} action{{ heroPowerActionCount(hero) === 1 ? '' : 's' }}
                    </div>
                  </td>
                  <td class="ui-table-cell">
                    <span v-if="hero.faction_slug" class="ui-status-badge ui-status-info">
                      {{ hero.faction_slug }}
                    </span>
                    <span v-else class="text-sm text-gray-500 dark:text-gray-400">Common</span>
                  </td>
                  <td class="ui-table-cell text-right text-gray-700 dark:text-gray-300">
                    {{ scopedCardsForHero(hero).length }}
                  </td>
                  <td class="ui-table-cell text-right text-gray-500 dark:text-gray-400">
                    v{{ hero.version }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-else class="ui-panel">
          <div class="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h2 class="ui-panel-title">Cards</h2>
              <p class="ui-panel-subtitle">Latest card templates and their current hero scope.</p>
            </div>

            <div class="grid gap-3 sm:grid-cols-[minmax(14rem,1fr)_11rem_11rem] lg:w-[42rem]">
              <label>
                <span class="ui-label">Search</span>
                <input
                  v-model.trim="searchQuery"
                  type="search"
                  class="ui-input mt-2"
                  placeholder="Name or slug"
                />
              </label>
              <label>
                <span class="ui-label">Type</span>
                <select v-model="cardTypeFilter" class="ui-select mt-2">
                  <option value="all">All types</option>
                  <option value="creature">Creatures</option>
                  <option value="spell">Spells</option>
                </select>
              </label>
              <label>
                <span class="ui-label">Scope</span>
                <select v-model="scopeFilter" class="ui-select mt-2">
                  <option value="all">All scopes</option>
                  <option value="global">All heroes</option>
                  <option value="hero">Hero scoped</option>
                </select>
              </label>
            </div>
          </div>

          <div v-if="filteredCards.length === 0" class="ui-panel-muted text-sm text-gray-500 dark:text-gray-400">
            No cards match the current filters.
          </div>

          <div v-else class="ui-table-wrap">
            <table class="ui-table">
              <thead class="bg-gray-50 dark:bg-gray-800/70">
                <tr>
                  <th class="ui-table-head">Card</th>
                  <th class="ui-table-head">Type</th>
                  <th class="ui-table-head text-right">Cost</th>
                  <th class="ui-table-head">Stats</th>
                  <th class="ui-table-head">Hero scope</th>
                  <th class="ui-table-head">Collectible</th>
                  <th class="ui-table-head text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-800 dark:bg-gray-900/40">
                <tr v-for="card in filteredCards" :key="card.id">
                  <td class="ui-table-cell">
                    <div class="font-medium text-gray-900 dark:text-white">{{ card.name }}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">{{ card.slug }}</div>
                  </td>
                  <td class="ui-table-cell">
                    <span class="ui-status-badge ui-status-neutral capitalize">
                      {{ card.card_type }}
                    </span>
                  </td>
                  <td class="ui-table-cell text-right font-semibold text-gray-900 dark:text-white">
                    {{ card.cost }}
                  </td>
                  <td class="ui-table-cell text-gray-700 dark:text-gray-300">
                    <span v-if="card.card_type === 'creature'">
                      {{ card.attack ?? 0 }} / {{ card.health ?? 0 }}
                    </span>
                    <span v-else class="text-gray-500 dark:text-gray-400">-</span>
                  </td>
                  <td class="ui-table-cell">
                    <span
                      :class="[
                        'ui-status-badge',
                        cardHeroSlugs(card).length ? 'ui-status-info' : 'ui-status-success'
                      ]"
                    >
                      {{ cardHeroScopeLabel(card) }}
                    </span>
                  </td>
                  <td class="ui-table-cell">
                    <span
                      :class="[
                        'ui-status-badge',
                        card.is_collectible === false ? 'ui-status-neutral' : 'ui-status-success'
                      ]"
                    >
                      {{ card.is_collectible === false ? 'No' : 'Yes' }}
                    </span>
                  </td>
                  <td class="ui-table-cell text-right">
                    <div class="flex justify-end gap-2">
                      <router-link
                        :to="{ name: 'CardDetails', params: { slug, cardSlug: card.slug } }"
                        class="ui-btn ui-btn-xs ui-btn-secondary"
                      >
                        View
                      </router-link>
                      <router-link
                        :to="{ name: 'CardEdit', params: { slug, cardSlug: card.slug } }"
                        class="ui-btn ui-btn-xs ui-btn-primary"
                      >
                        Edit
                      </router-link>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, FileCode2, Loader2, Plus } from 'lucide-vue-next'
import axios from '../config/api'
import { useNotificationStore } from '../stores/notifications'
import { useTitleStore } from '../stores/title'

interface TitleSummary {
  slug: string
  name: string
}

interface HeroConfig {
  id: number
  slug: string
  name: string
  description: string
  version: number
  health: number
  hero_power: {
    name?: string
    description?: string
    actions?: unknown[]
  }
  spec: Record<string, unknown>
  faction_slug: string | null
  art_url: string | null
}

interface CardConfig {
  id: number
  slug: string
  name: string
  description: string
  version: number
  card_type: 'creature' | 'spell'
  cost: number
  attack: number | null
  health: number | null
  spec: Record<string, unknown>
  is_collectible: boolean
  faction_slug: string | null
  art_url: string | null
  hero_slugs?: string[]
}

interface ContentConfigResponse {
  title: TitleSummary
  heroes: HeroConfig[]
  cards: CardConfig[]
}

const tabs = [
  { id: 'heroes', name: 'Heroes' },
  { id: 'cards', name: 'Cards' }
] as const

type TabId = typeof tabs[number]['id']

const route = useRoute()
const titleStore = useTitleStore()
const notificationStore = useNotificationStore()

const slug = computed(() => route.params.slug as string)
const loading = ref(true)
const error = ref<string | null>(null)
const content = ref<ContentConfigResponse | null>(null)
const activeTab = ref<TabId>('heroes')
const searchQuery = ref('')
const cardTypeFilter = ref<'all' | 'creature' | 'spell'>('all')
const scopeFilter = ref<'all' | 'global' | 'hero'>('all')

const pageTitle = computed(() => content.value?.title.name || titleStore.currentTitle?.name || 'World')
const heroes = computed(() => content.value?.heroes || [])
const cards = computed(() => content.value?.cards || [])
const heroLookup = computed(() => new Map(heroes.value.map(hero => [hero.slug, hero])))

const collectibleCardCount = computed(() => (
  cards.value.filter(card => card.is_collectible !== false).length
))

const heroScopedCardCount = computed(() => (
  cards.value.filter(card => cardHeroSlugs(card).length > 0).length
))

const filteredCards = computed(() => {
  const query = searchQuery.value.toLowerCase()

  return cards.value.filter(card => {
    if (cardTypeFilter.value !== 'all' && card.card_type !== cardTypeFilter.value) {
      return false
    }

    const heroSlugs = cardHeroSlugs(card)
    if (scopeFilter.value === 'global' && heroSlugs.length > 0) return false
    if (scopeFilter.value === 'hero' && heroSlugs.length === 0) return false

    if (!query) return true
    return (
      card.name.toLowerCase().includes(query) ||
      card.slug.toLowerCase().includes(query)
    )
  })
})

const readStringArray = (value: unknown): string[] => {
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
  }
  if (typeof value === 'string' && value.trim()) {
    return [value.trim()]
  }
  return []
}

const cardHeroSlugs = (card: CardConfig): string[] => {
  const direct = readStringArray(card.hero_slugs)
  if (direct.length) return direct

  const spec = card.spec || {}
  const candidates = [
    spec.hero_slugs,
    spec.hero_slug,
    spec.allowed_heroes,
    spec.allowedHeroes,
    spec.heroes,
    spec.hero
  ]

  for (const candidate of candidates) {
    const slugs = readStringArray(candidate)
    if (slugs.length) return slugs
  }

  return []
}

const cardHeroScopeLabel = (card: CardConfig): string => {
  const heroSlugs = cardHeroSlugs(card)
  if (!heroSlugs.length) return 'All heroes'

  return heroSlugs
    .map(heroSlug => heroLookup.value.get(heroSlug)?.name || heroSlug)
    .join(', ')
}

const scopedCardsForHero = (hero: HeroConfig): CardConfig[] => (
  cards.value.filter(card => cardHeroSlugs(card).includes(hero.slug))
)

const heroPowerName = (hero: HeroConfig): string => {
  return hero.hero_power?.name || 'Power'
}

const heroPowerActionCount = (hero: HeroConfig): number => {
  return Array.isArray(hero.hero_power?.actions) ? hero.hero_power.actions.length : 0
}

const fetchContent = async (): Promise<void> => {
  try {
    loading.value = true
    error.value = null
    const response = await axios.get<ContentConfigResponse>(`/builder/titles/${slug.value}/content/`)
    content.value = response.data
  } catch (err) {
    console.error('Error loading heroes and cards:', err)
    error.value = 'Failed to load heroes and cards.'
    notificationStore.handleApiError(err as Error)
  } finally {
    loading.value = false
  }
}

onMounted(fetchContent)

watch(slug, () => {
  void fetchContent()
})
</script>

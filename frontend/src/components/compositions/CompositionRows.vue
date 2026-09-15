<template>
  <div class="divide-y divide-gray-200 dark:divide-gray-800">
    <router-link
      v-for="(row, index) in rows" :key="row.composition.code"
      :to="{ name: 'CompositionDetail', params: { slug: titleSlug, code: row.composition.code }, query: detailQuery }"
      class="group grid gap-4 px-4 py-5 transition-colors hover:bg-primary-50/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary-500 dark:hover:bg-primary-950/20 sm:px-6 md:grid-cols-[minmax(0,1fr)_9rem_6rem] md:items-center"
    >
      <div class="flex min-w-0 gap-4">
        <span class="hidden w-6 flex-none pt-1 text-sm tabular-nums text-gray-400 sm:block">{{ offset + index + 1 }}</span>
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="font-semibold text-gray-900 group-hover:text-primary-700 dark:text-white dark:group-hover:text-primary-300">{{ compositionLabel(row.composition) }}</h3>
            <ChevronRight class="h-4 w-4 text-gray-400 group-hover:text-primary-500" aria-hidden="true" />
          </div>
          <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {{ row.composition.total_cards }} cards · {{ row.composition.cards?.length || 0 }} unique
            <span v-if="row.composition.digest" class="ml-1 font-mono">· {{ row.composition.digest.slice(0, 6) }}</span>
          </p>
          <div class="mt-3 flex flex-wrap gap-1.5">
            <span v-for="card in compositionPreviewCards(row.composition)" :key="card.slug" class="rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300">
              <span class="font-semibold text-primary-700 dark:text-primary-300">{{ card.count }}×</span> {{ card.name || card.slug }}
            </span>
            <span v-if="(row.composition.cards?.length || 0) > 4" class="px-1 py-1 text-xs text-gray-500">+{{ row.composition.cards!.length - 4 }} more</span>
          </div>
        </div>
      </div>
      <div class="flex items-center justify-between gap-5 sm:ml-10 md:ml-0 md:block">
        <div class="w-36">
          <p :class="['text-xl font-bold tabular-nums', row.record.win_rate! >= 0.5 ? 'text-emerald-700 dark:text-emerald-400' : 'text-gray-800 dark:text-gray-200']">
            {{ ((row.record.win_rate || 0) * 100).toFixed(1) }}<span class="text-sm">%</span>
            <span class="ml-1 text-xs font-normal text-gray-500 dark:text-gray-400">win rate</span>
          </p>
          <div class="relative mt-2 h-1.5 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700" aria-hidden="true">
            <div class="h-full rounded-full bg-primary-500" :style="{ width: `${(row.record.win_rate || 0) * 100}%` }" />
            <span class="absolute inset-y-0 left-1/2 w-px bg-gray-900/40 dark:bg-white/60" />
          </div>
        </div>
        <p class="mt-2 text-xs tabular-nums text-gray-500 dark:text-gray-400">{{ row.record.wins }}W · {{ row.record.losses }}L · {{ row.record.draws }}D</p>
      </div>
      <div class="flex items-center gap-2 sm:ml-10 md:ml-0 md:block md:text-right">
        <p class="text-sm font-semibold tabular-nums text-gray-800 dark:text-gray-200">{{ row.record.games.toLocaleString() }} <span class="font-normal text-gray-500">uses</span></p>
        <span v-if="row.record.games < 20" class="mt-1 inline-block text-xs text-amber-700 dark:text-amber-400" title="Fewer than 20 recorded uses. Results may change substantially with more games.">Small sample</span>
      </div>
    </router-link>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronRight } from 'lucide-vue-next'
import type { CompositionBrowseRow } from '../../types/composition'
import { compositionLabel, compositionPreviewCards } from '../../utils/compositions'
defineProps<{ rows: CompositionBrowseRow[]; titleSlug: string; offset: number }>()
const route = useRoute()
const detailQuery = computed(() => {
  const query = { ...route.query }
  delete query.matchup_page
  return query
})
</script>

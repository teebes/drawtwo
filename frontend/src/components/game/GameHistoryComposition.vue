<template>
  <router-link
    v-if="composition"
    :to="{
      name: 'CompositionDetail',
      params: { slug: titleSlug, code: composition.code },
      query: gameType === 'friendly' ? { game_type: 'friendly' } : {}
    }"
    class="group flex min-w-0 items-center gap-3 bg-white px-3 py-2.5 transition-colors hover:bg-primary-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary-500 dark:bg-gray-900/70 dark:hover:bg-gray-800"
    :aria-label="`${label}: ${compositionLabel(composition)}`"
  >
    <Layers class="h-4 w-4 flex-none text-gray-400 group-hover:text-primary-500" aria-hidden="true" />
    <div class="min-w-0 flex-1">
      <p class="text-xs text-gray-500 dark:text-gray-400">{{ label }}</p>
      <p class="truncate text-sm font-medium text-secondary-700 group-hover:underline dark:text-secondary-400" :title="compositionLabel(composition)">
        {{ compositionLabel(composition) }}
      </p>
    </div>
    <ChevronRight class="h-4 w-4 flex-none text-gray-400 group-hover:text-primary-500" aria-hidden="true" />
  </router-link>
  <div v-else class="flex min-w-0 items-center gap-3 bg-white px-3 py-2.5 dark:bg-gray-900/70">
    <Layers class="h-4 w-4 flex-none text-gray-400" aria-hidden="true" />
    <div>
      <p class="text-xs text-gray-500 dark:text-gray-400">{{ label }}</p>
      <p class="text-sm text-gray-500 dark:text-gray-400">{{ unavailableText }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronRight, Layers } from 'lucide-vue-next'
import type { DeckCompositionSummary } from '../../types/composition'
import { compositionLabel } from '../../utils/compositions'

withDefaults(defineProps<{
  label: string
  composition?: DeckCompositionSummary | null
  titleSlug: string
  gameType: string
  unavailableText?: string
}>(), { unavailableText: 'Not recorded' })
</script>

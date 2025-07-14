<template>
  <div class="group transform transition-all duration-300 hover:-translate-y-2 hover:shadow-xl">
    <div :class="[
      'h-96 w-full max-w-lg mx-auto overflow-hidden rounded-xl border-2 p-1',
      borderClass,
      backgroundClass
    ]">
      <div class="flex h-full flex-col rounded-lg bg-white p-4 dark:bg-gray-900">
        <!-- Header with name and cost -->
        <div class="flex items-center justify-between mb-3">
          <h4 class="font-display text-lg font-bold text-gray-900 dark:text-white truncate mr-2">
            {{ card.name }}
          </h4>
          <div :class="[
            'flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold text-white shrink-0',
            costBgClass
          ]">
            {{ card.cost }}
          </div>
        </div>

        <!-- Type line -->
        <div class="text-sm text-gray-600 dark:text-gray-400 mb-3 capitalize">
          {{ card.card_type }}
          <span v-if="card.card_type === 'minion'" class="text-gray-500">Creature</span>
        </div>

        <!-- Card text -->
        <div class="text-sm text-gray-800 dark:text-gray-200 flex-1 mb-3">
          {{ card.description }}
        </div>

        <!-- Traits -->
        <div v-if="card.traits && card.traits.length > 0" class="mb-3">
          <div class="flex flex-wrap gap-1">
            <span
              v-for="trait in card.traits"
              :key="trait.slug"
              class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"
            >
              {{ trait.name }}
              <span v-if="getTraitValue(trait)" class="ml-1 font-bold">{{ getTraitValue(trait) }}</span>
            </span>
          </div>
        </div>

        <!-- Stats (for minions) -->
        <div v-if="card.card_type === 'minion'" class="flex justify-between items-center">
          <div class="text-sm text-gray-600 dark:text-gray-400">Attack / Health</div>
          <div class="rounded bg-gray-200 px-3 py-1 text-sm font-bold text-gray-800 dark:bg-gray-700 dark:text-gray-200">
            {{ card.attack }}/{{ card.health }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Card } from '../../types/card'

interface Props {
  card: Card
}

const props = defineProps<Props>()

const borderClass = computed(() => {
  const borderMap = {
    spell: 'border-blue-500',
    minion: 'border-yellow-500'
  }
  return borderMap[props.card.card_type]
})

const backgroundClass = computed(() => {
  const bgMap = {
    spell: 'bg-gradient-to-b from-blue-50 to-blue-100 dark:from-blue-900/50 dark:to-blue-800/50',
    minion: 'bg-gradient-to-b from-yellow-50 to-yellow-100 dark:from-yellow-900/50 dark:to-yellow-800/50'
  }
  return bgMap[props.card.card_type]
})

const costBgClass = computed(() => {
  const costMap = {
    spell: 'bg-blue-500',
    minion: 'bg-red-500'
  }
  return costMap[props.card.card_type]
})

const getTraitValue = (trait: Card['traits'][0]) => {
  // Check for common value patterns in the data object
  if (trait.data.value !== undefined) {
    return trait.data.value
  }
  if (trait.data.armor !== undefined) {
    return trait.data.armor
  }
  if (trait.data.amount !== undefined) {
    return trait.data.amount
  }
  // Return null if no displayable value found
  return null
}
</script>
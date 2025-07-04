<template>
  <div :class="[
    'relative flex flex-col justify-between rounded-lg border-2 p-2 shadow-md transition-all duration-200',
    'bg-white dark:bg-gray-800',
    cardTypeClass,
    exhaustedClass,
    'min-w-16 max-w-20'
  ]">
    <!-- Exhausted Indicator -->
    <div v-if="card.exhausted" class="absolute -top-1 -right-1 w-4 h-4 bg-red-600 rounded-full flex items-center justify-center">
      <span class="text-white text-xs font-bold">⚡</span>
    </div>

    <!-- Card Name -->
    <div class="mb-1 text-xs font-medium text-gray-900 dark:text-white leading-tight break-words">
      {{ name }}
    </div>

    <!-- Stats Row -->
    <div v-if="cardType === 'minion'" class="flex justify-between items-center text-xs font-bold">
      <span :class="['px-1 py-0.5 rounded bg-red-500 text-white min-w-4 text-center']">
        {{ attack }}
      </span>
      <span :class="['px-1 py-0.5 rounded bg-green-500 text-white min-w-4 text-center']">
        {{ health }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CardInPlay } from '../../types/game'

interface Props {
  card: CardInPlay
  name: string
  cardType: 'minion' | 'spell'
}

const props = defineProps<Props>()

const cardTypeClass = computed(() => {
  return props.cardType === 'minion'
    ? 'border-yellow-400 bg-gradient-to-b from-yellow-50 to-yellow-100 dark:from-yellow-900/30 dark:to-yellow-800/30'
    : 'border-blue-400 bg-gradient-to-b from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30'
})

const exhaustedClass = computed(() => {
  if (props.card.exhausted) {
    return 'opacity-50 grayscale cursor-not-allowed pointer-events-none'
  } else {
    return 'hover:scale-105 cursor-pointer'
  }
})

const attack = computed(() => props.card.attack)
const health = computed(() => props.card.health)
</script>
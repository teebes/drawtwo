<template>
  <div :class="[
    'relative flex flex-col justify-between rounded-lg border-2 p-2 shadow-md transition-all duration-200',
    'bg-white dark:bg-gray-800',
    cardTypeClass,
    exhaustedClass,
    'min-w-16 max-w-20',
    {
      'ring-2 ring-blue-500 ring-offset-2': isSelected,
      'ring-2 ring-red-500 ring-offset-2 animate-pulse': isTargetable,
      'scale-110 z-10': isAttacker
    }
  ]"
  @click="handleClick"
  :data-card-id="card.card_id">
    <!-- Stealth Indicator -->
    <div v-if="hasStealth" class="absolute -top-1 -left-1 w-4 h-4 bg-purple-600 rounded-full flex items-center justify-center" title="Stealth">
      <span class="text-xs">👁️</span>
    </div>

    <!-- Exhausted Indicator -->
    <div v-if="card.exhausted" class="absolute -top-1 -right-1 w-4 h-4 bg-gray-600 rounded-full flex items-center justify-center">
      <span class="text-white text-xs font-bold">z</span>
    </div>

    <!-- Card Name -->
    <div class="mb-1 text-xs font-medium text-gray-900 dark:text-white leading-tight break-words">
      {{ name }}
    </div>

    <!-- Stats Row -->
    <div v-if="cardType === 'creature'" class="flex justify-between items-center text-xs font-bold">
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
  cardType: 'creature' | 'spell'
  isCanAttack?: boolean
  isSelected?: boolean
  isTargetable?: boolean
  isAttacker?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'card-clicked': [cardId: string]
}>()

const cardTypeClass = computed(() => {
  return props.cardType === 'creature'
    ? 'border-yellow-400 bg-gradient-to-b from-yellow-50 to-yellow-100 dark:from-yellow-900/30 dark:to-yellow-800/30'
    : 'border-blue-400 bg-gradient-to-b from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30'
})

const exhaustedClass = computed(() => {
  if (props.card.exhausted && !props.isCanAttack) {
    return 'opacity-50 grayscale'
  } else if (props.isCanAttack || props.isTargetable) {
    return 'hover:scale-105 cursor-pointer'
  }
  return ''
})

const attack = computed(() => props.card.attack)
const health = computed(() => props.card.health)

const hasStealth = computed(() => {
  return props.card.traits?.some(trait => trait.type === 'stealth') ?? false
})

const handleClick = () => {
  if (props.isCanAttack || props.isTargetable) {
    emit('card-clicked', String(props.card.card_id))
  }
}
</script>
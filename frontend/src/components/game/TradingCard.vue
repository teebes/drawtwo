<template>
  <div class="group transform transition-all duration-300 hover:-translate-y-2 hover:shadow-xl">
    <div :class="[
      'h-96 w-64 overflow-hidden rounded-xl border-2 p-1',
      borderClass,
      backgroundClass
    ]">
      <div class="flex h-full flex-col rounded-lg bg-white p-4 dark:bg-gray-900">
        <!-- Header with name and cost -->
        <div class="flex items-center justify-between">
          <h4 class="font-display text-lg font-bold text-gray-900 dark:text-white">{{ name }}</h4>
          <div :class="[
            'flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold text-white',
            costBgClass
          ]">
            {{ cost }}
          </div>
        </div>

        <!-- Art/Icon section -->
        <div :class="[
          'my-4 flex flex-1 items-center justify-center rounded text-6xl',
          artBackgroundClass
        ]">
          {{ icon }}
        </div>

        <!-- Type line -->
        <div class="text-sm text-gray-600 dark:text-gray-400 mb-2">{{ type }}</div>

        <!-- Card text -->
        <div class="text-sm text-gray-800 dark:text-gray-200 flex-1">
          {{ text }}
        </div>

        <!-- Stats (for creatures) -->
        <div v-if="power !== undefined && toughness !== undefined" class="flex justify-end mt-2">
          <div class="rounded bg-gray-200 px-3 py-1 text-sm font-bold text-gray-800 dark:bg-gray-700 dark:text-gray-200">
            {{ power }}/{{ toughness }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  name: string
  cost: string | number
  icon: string
  type: string
  text: string
  rarity?: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary' | 'mythic'
  cardType?: 'spell' | 'creature' | 'equipment' | 'artifact'
  power?: number
  toughness?: number
}

const props = withDefaults(defineProps<Props>(), {
  rarity: 'common',
  cardType: 'spell'
})

const borderClass = computed(() => {
  const borderMap = {
    spell: 'border-blue-500',
    creature: 'border-yellow-500',
    equipment: 'border-purple-500',
    artifact: 'border-gray-500'
  }
  return borderMap[props.cardType]
})

const backgroundClass = computed(() => {
  const bgMap = {
    spell: 'bg-gradient-to-b from-blue-50 to-blue-100 dark:from-blue-900/50 dark:to-blue-800/50',
    creature: 'bg-gradient-to-b from-yellow-50 to-yellow-100 dark:from-yellow-900/50 dark:to-yellow-800/50',
    equipment: 'bg-gradient-to-b from-purple-50 to-purple-100 dark:from-purple-900/50 dark:to-purple-800/50',
    artifact: 'bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900/50 dark:to-gray-800/50'
  }
  return bgMap[props.cardType]
})

const costBgClass = computed(() => {
  const costMap = {
    spell: 'bg-blue-500',
    creature: 'bg-red-500',
    equipment: 'bg-purple-500',
    artifact: 'bg-gray-500'
  }
  return costMap[props.cardType]
})

const artBackgroundClass = computed(() => {
  const artMap = {
    spell: 'bg-gradient-to-br from-yellow-200 to-blue-300',
    creature: 'bg-gradient-to-br from-red-200 to-orange-300',
    equipment: 'bg-gradient-to-br from-gray-200 to-purple-300',
    artifact: 'bg-gradient-to-br from-gray-200 to-gray-300'
  }
  return artMap[props.cardType]
})
</script>
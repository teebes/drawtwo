<template>
  <div :class="[
    'flex items-center justify-between p-3 rounded-lg border-2 border-purple-500',
    'bg-gradient-to-r from-purple-100 to-purple-200 dark:from-purple-900/30 dark:to-purple-800/30',
    'shadow-lg'
  ]">
    <!-- Hero Name -->
    <div class="flex flex-col">
      <h3 class="font-display text-lg font-bold text-gray-900 dark:text-white">
        {{ hero.name }}
      </h3>
    </div>

    <!-- Health -->
    <div class="flex items-center space-x-2">
      <span class="font-bold text-lg text-red-600 dark:text-red-400 ml-4">
        {{ hero.health }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { HeroInPlay } from '../../types/game'

interface Props {
  hero: HeroInPlay
}

defineProps<Props>()
</script>
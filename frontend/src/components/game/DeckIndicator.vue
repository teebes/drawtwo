<template>
  <div :class="[
    'flex items-center space-x-2 px-3 py-2 rounded-lg border',
    'bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600',
    'shadow-md'
  ]">
    <div class="text-xl">🃏</div>
    <span class="font-bold text-sm text-gray-900 dark:text-white">
      {{ cardCount }}
    </span>
  </div>
</template>

<script setup lang="ts">
interface Props {
  cardCount: number
}

defineProps<Props>()
</script>
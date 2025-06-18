<template>
  <div class="flex items-center space-x-3 rounded-lg bg-gray-100 p-3 dark:bg-gray-800">
    <div :class="['h-6 w-6 rounded-full', colorClass]"></div>
    <span class="text-sm font-medium text-gray-900 dark:text-white">{{ name }}</span>
  </div>
</template>

<script setup lang="ts">
interface Props {
  name: string
  colorClass: string
}

defineProps<Props>()
</script>
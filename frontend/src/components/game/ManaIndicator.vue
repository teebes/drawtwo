<template>
  <div class="flex items-center justify-center space-x-2 bg-blue-900/40 rounded-lg px-3 py-2 border border-blue-400/30">
    <div class="flex items-center space-x-1">
      <div class="w-4 h-4 bg-blue-400 rounded-full"></div>
      <span class="text-blue-300 text-sm font-medium">{{ manaUsed }}/{{ manaPool }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  manaPool: number
  manaUsed: number
}

const props = defineProps<Props>()
</script>
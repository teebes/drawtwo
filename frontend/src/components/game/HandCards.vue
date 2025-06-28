<template>
  <div class="flex items-center">
    <div class="flex space-x-1 max-w-full overflow-x-auto">
      <div v-for="cardId in handCards.slice(0, maxCards)" :key="cardId"
        class="flex-shrink-0 w-12 h-16 bg-gradient-to-b from-amber-400 to-amber-600 rounded border border-amber-300/50 shadow-sm flex items-center justify-center">
        <div class="text-xs text-amber-900 font-bold">{{ cardId }}</div>
      </div>
      <div v-if="handCards.length === 0" class="text-gray-400 text-xs py-2">
        No cards
      </div>
      <div v-if="handCards.length > maxCards" class="flex-shrink-0 text-gray-400 text-xs py-2">
        +{{ handCards.length - maxCards }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  handCards: number[]
  maxCards?: number
}

const props = withDefaults(defineProps<Props>(), {
  maxCards: 4
})
</script>

<style scoped>
/* Custom scrollbar for horizontal card overflow */
.overflow-x-auto::-webkit-scrollbar {
  height: 2px;
}

.overflow-x-auto::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 1px;
}

.overflow-x-auto::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 1px;
}

.overflow-x-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}
</style>
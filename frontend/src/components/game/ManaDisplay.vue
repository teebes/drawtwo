<template>
  <div>
    <p v-if="label" class="text-sm text-gray-600 dark:text-gray-400 mb-2">{{ label }}</p>
    <div class="flex space-x-1">
      <div
        v-for="crystal in totalCrystals"
        :key="crystal"
        :class="[
          'h-6 w-6 rounded-full',
          crystal <= currentMana ? 'bg-blue-500' : 'bg-gray-300',
          crystal === currentMana && animate ? 'animate-mana-pulse' : ''
        ]"
      ></div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  currentMana: number
  totalCrystals: number
  animate?: boolean
  label?: string
}

withDefaults(defineProps<Props>(), {
  animate: false
})
</script>
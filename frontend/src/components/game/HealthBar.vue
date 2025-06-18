<template>
  <div>
    <p v-if="label" class="text-sm text-gray-600 dark:text-gray-400 mb-2">{{ label }}</p>
    <div class="flex items-center space-x-2">
      <div :class="['h-3 rounded-full bg-gray-300', widthClass]">
        <div
          :class="[
            'h-3 rounded-full transition-all duration-300',
            colorClass
          ]"
          :style="{ width: `${percentage}%` }"
        ></div>
      </div>
      <span class="font-mono text-sm text-gray-900 dark:text-white">
        {{ current }}/{{ max }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  current: number
  max: number
  label?: string
  width?: 'sm' | 'md' | 'lg'
  color?: 'red' | 'green' | 'blue' | 'yellow'
}

const props = withDefaults(defineProps<Props>(), {
  width: 'md',
  color: 'red'
})

const percentage = computed(() => Math.round((props.current / props.max) * 100))

const widthClass = computed(() => {
  const widthMap = {
    sm: 'w-24',
    md: 'w-32',
    lg: 'w-48'
  }
  return widthMap[props.width]
})

const colorClass = computed(() => {
  const colorMap = {
    red: 'bg-red-500',
    green: 'bg-green-500',
    blue: 'bg-blue-500',
    yellow: 'bg-yellow-500'
  }
  return colorMap[props.color]
})
</script>
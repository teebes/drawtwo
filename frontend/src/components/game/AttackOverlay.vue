<template>
  <svg
    class="fixed inset-0 pointer-events-none z-50"
    style="width: 100vw; height: 100vh"
  >
    <defs>
      <marker
        id="arrowhead"
        markerWidth="10"
        markerHeight="7"
        refX="10"
        refY="3.5"
        orient="auto"
      >
        <polygon
          points="0 0, 10 3.5, 0 7"
          fill="#ef4444"
        />
      </marker>
    </defs>
    <line
      v-if="fromPosition && toPosition"
      :x1="fromPosition.x"
      :y1="fromPosition.y"
      :x2="toPosition.x"
      :y2="toPosition.y"
      stroke="#ef4444"
      stroke-width="4"
      marker-end="url(#arrowhead)"
      class="animate-attack"
    />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Position {
  x: number
  y: number
}

interface Props {
  fromElement: HTMLElement | null
  toElement: HTMLElement | null
}

const props = defineProps<Props>()

const fromPosition = computed<Position | null>(() => {
  if (!props.fromElement) return null
  const rect = props.fromElement.getBoundingClientRect()
  return {
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2
  }
})

const toPosition = computed<Position | null>(() => {
  if (!props.toElement) return null
  const rect = props.toElement.getBoundingClientRect()
  return {
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2
  }
})
</script>

<style scoped>
/* Animation is now handled by Tailwind's animate-attack class */
</style>
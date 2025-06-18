<template>
  <div :class="[
    'rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800',
    paddingClass,
    customClass
  ]">
    <h3 v-if="title" :class="titleClass">{{ title }}</h3>
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  title?: string
  padding?: 'sm' | 'md' | 'lg' | 'xl'
  customClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  padding: 'md'
})

const paddingClass = computed(() => {
  const paddingMap = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
    xl: 'p-10'
  }
  return paddingMap[props.padding]
})

const titleClass = 'mb-4 text-lg font-semibold text-gray-900 dark:text-white'
</script>
<template>
  <div :class="[
    'rounded-xl p-6 shadow-sm flex flex-col',
    variantClass,
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
  variant?: 'default' | 'error' | 'success'
  customClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  padding: 'md',
  variant: 'default'
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

const variantClass = computed(() => {
  const variantMap = {
    default: 'bg-white dark:bg-gray-800',
    error: 'bg-red-500/20 border border-red-400/30',
    success: 'bg-green-500/20 border border-green-400/30'
  }
  return variantMap[props.variant]
})

const titleClass = 'mb-4 text-lg font-semibold text-gray-900 dark:text-white'
</script>
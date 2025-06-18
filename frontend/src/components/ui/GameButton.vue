<template>
  <button
    :class="[
      'transition-all font-medium',
      sizeClass,
      variantClass,
      customClass
    ]"
    v-bind="$attrs"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  variant?: 'primary' | 'secondary' | 'danger' | 'gradient'
  size?: 'sm' | 'md' | 'lg'
  customClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md'
})

const sizeClass = computed(() => {
  const sizeMap = {
    sm: 'px-3 py-1.5 text-sm rounded-md',
    md: 'px-4 py-2 text-sm rounded-lg',
    lg: 'px-6 py-3 text-base rounded-xl'
  }
  return sizeMap[props.size]
})

const variantClass = computed(() => {
  const variantMap = {
    primary: 'bg-primary-600 text-white hover:bg-primary-700',
    secondary: 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700',
    danger: 'bg-red-600 text-white hover:bg-red-700',
    gradient: 'bg-gradient-to-r from-primary-600 to-secondary-600 text-white shadow-lg hover:from-primary-700 hover:to-secondary-700'
  }
  return variantMap[props.variant]
})
</script>
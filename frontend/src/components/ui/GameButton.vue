<template>
  <button
    :class="[
      'ui-btn',
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
  size?: 'xs' | 'sm' | 'md' | 'lg'
  customClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md'
})

const sizeClass = computed(() => {
  const sizeMap = {
    xs: 'ui-btn-xs',
    sm: 'ui-btn-sm',
    md: 'ui-btn-md',
    lg: 'ui-btn-lg'
  }
  return sizeMap[props.size]
})

const variantClass = computed(() => {
  const variantMap = {
    primary: 'ui-btn-primary',
    secondary: 'ui-btn-secondary',
    danger: 'ui-btn-danger',
    gradient: 'ui-btn-gradient'
  }
  return variantMap[props.variant]
})
</script>

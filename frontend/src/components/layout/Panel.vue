<template>
  <div :class="[
    variantClass,
    paddingClass,
    customClass
  ]">
    <h3 v-if="title" class="ui-panel-title mb-4">{{ title }}</h3>
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
    default: 'ui-panel',
    error: 'ui-alert ui-alert-error',
    success: 'ui-alert ui-alert-success'
  }
  return variantMap[props.variant]
})
</script>

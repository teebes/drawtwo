<template>
  <div class="rounded-lg border border-gray-200 dark:border-gray-700">
    <!-- Grid of color variations -->
    <div v-if="variations" class="grid grid-cols-5">
      <div
        v-for="(variant, index) in variations"
        :key="index"
        :class="[
          'h-16 flex items-center justify-center text-xs font-mono',
          variant.bgClass,
          variant.textClass || (index > 1 ? 'text-white' : '')
        ]"
      >
        {{ variant.weight }}
      </div>
    </div>

    <!-- Single color swatch -->
    <div v-else-if="color" :class="['h-16 flex items-center justify-center', color]">
      <slot name="content" />
    </div>

    <!-- Label -->
    <div class="p-2 text-sm font-medium text-gray-700 dark:text-gray-300">
      {{ label }}
    </div>
  </div>
</template>

<script setup lang="ts">
interface ColorVariation {
  weight: string
  bgClass: string
  textClass?: string
}

interface Props {
  label: string
  variations?: ColorVariation[]
  color?: string
}

defineProps<Props>()
</script>
<template>
  <section :class="['mb-16', customClass]">
    <h2 class="mb-8 font-display text-3xl font-bold text-gray-900 dark:text-white">
      {{ title }}
    </h2>
    <p v-if="subtitle" class="mb-8 text-lg text-gray-600 dark:text-gray-300">
      {{ subtitle }}
    </p>
    <slot />
  </section>
</template>

<script setup lang="ts">
interface Props {
  title: string
  subtitle?: string
  customClass?: string
}

defineProps<Props>()
</script>
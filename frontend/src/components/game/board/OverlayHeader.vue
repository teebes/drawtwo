<template>
    <div
        class="overlay-header flex flex-row w-full border-b border-gray-700 items-center"
        :class="{ 'overlay-header--compact': compact }">
        <!-- Display Text -->
        <div class="flex-1 text-center text-gray-400">{{ text }}</div>

        <!-- Close Button-->
        <div
          class="overlay-header-close h-full flex items-center justify-center cursor-pointer group relative border-l border-gray-700"
          @click="$emit('close')"
          title="Click to close overlay"
        >
          <svg
            class="overlay-header-close-icon text-gray-500 group-hover:text-gray-100 pointer-events-none"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true">
            <path
              d="M5 5L19 19M19 5L5 19"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="square" />
          </svg>
          <span class="sr-only">Close overlay</span>
        </div>
    </div>
</template>

<script setup lang="ts">
defineProps<{
    text: string | null
    compact?: boolean
}>()

defineEmits<{
    close: []
}>()
</script>

<style scoped>
.overlay-header {
    height: 6rem;
}

.overlay-header-close {
    width: 6rem;
}

.overlay-header-close-icon {
    width: 2.5rem;
    height: 2.5rem;
}

.overlay-header--compact {
    height: calc(4.2rem + 1px);
}

.overlay-header--compact .overlay-header-close {
    width: calc(4.2rem + 1px);
}
</style>

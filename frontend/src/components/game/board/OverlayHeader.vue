<template>
    <div class="flex flex-row w-full h-24 border-b border-gray-700 items-center">
        <!-- Display Text -->
        <div class="flex-1 text-center text-gray-400">{{ text }}</div>

        <!-- Close Button-->
        <div
          class="w-24 h-full flex items-center justify-center cursor-pointer group relative border-l border-gray-700"
          @click="$emit('close')"
          title="Click to close overlay"
        >
          <span
            class="text-6xl text-gray-500 group-hover:text-gray-100 select-none pointer-events-none"
            style="line-height: 1;"
          >&times;</span>
          <span class="sr-only">Close overlay</span>
        </div>
    </div>
</template>

<script setup lang="ts">
defineProps<{
    text: string | null
}>()

defineEmits<{
    close: []
}>()
</script>

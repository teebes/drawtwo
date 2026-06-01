<template>
    <div class="update-entity w-10 border-2 border-gray-900 bg-gray-300 rounded-xl relative">
        <img v-if="props.art_url && !imageError"
            :src="props.art_url"
            :alt="props.name"
            class="absolute w-full h-full object-cover rounded-xl"
            @error="imageError = true">
    </div>
</template>



<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
    name: string
    art_url?: string | null
}

const props = defineProps<Props>()
const imageError = ref(false)

watch(
    () => props.art_url,
    () => {
        imageError.value = false
    }
)

</script>

<style scoped>
.update-entity {
    aspect-ratio: 5 / 7;
}
</style>

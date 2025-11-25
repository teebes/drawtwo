<template>
    <div class="update-entity w-10 border-2 border-gray-900 bg-gray-300 rounded-xl relative">
        <img v-if="props.art_url"
            :src="props.art_url"
            :alt="props.name"
            class="absolute w-full h-full object-cover rounded-xl">
    </div>
</template>



<script setup lang="ts">

interface Props {
    name: string
    art_url?: string | null
}

const props = defineProps<Props>()

</script>

<style scoped>
.update-entity {
    aspect-ratio: 5 / 7;
}
</style>
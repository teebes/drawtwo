<template>
    <div class="hero-detail-card border-2 border-gray-900 bg-gray-300 text-gray-900 rounded-xl relative overflow-visible">
        <img
            :src="heroArtUrl"
            :alt="`${hero.name} artwork`"
            class="absolute inset-0 w-full h-full object-cover rounded-[0.625rem]"
            @error="onHeroImageError"
        />

        <div
            class="hero-health-badge -bottom-3 -right-3 bg-green-600">
            {{ hero.health }}
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { HeroInPlay } from '@/types/game'

const props = defineProps<{
    hero: HeroInPlay
}>()

const heroImageError = ref(false)

const heroArtUrl = computed(() => {
    if (heroImageError.value) {
        return '/card_backs/placeholder.svg'
    }

    return props.hero.art_url || '/card_backs/placeholder.svg'
})

const onHeroImageError = () => {
    heroImageError.value = true
}
</script>

<style scoped>
.hero-detail-card {
    width: 100%;
    height: 100%;
    aspect-ratio: 5 / 7;
}

.hero-health-badge {
    @apply absolute text-white rounded-full w-10 h-10 flex font-bold items-center justify-center text-xs border border-gray-900 z-20 shadow-lg;
}
</style>

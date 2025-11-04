<template>
    <div class="w-24 h-full relative flex flex-col items-center justify-center border-r cursor-pointer hover:bg-gray-700/50 overflow-hidden transition-all"
         :class="activeClasses"
         @click="handleClick">
        <!-- Hero Art (fills whole area, cropped to fit) -->
        <img
            v-if="heroArtUrl && !imageError"
            :src="heroArtUrl"
            :alt="`${heroName} artwork`"
            class="absolute inset-0 w-full h-full object-cover"
            @error="onImageError"
        />
        <!-- Health overlay (takes up whole div) -->
        <div class="absolute inset-0 bg-black/50 flex items-center justify-center z-10">
            <div class="text-white font-bold">{{ health }}</div>
        </div>
        <!-- Turn indicator border -->
        <div v-if="active" class="absolute inset-0 border-4 border-yellow-500 z-20 pointer-events-none"></div>
    </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { HeroInPlay } from '@/types/game'

interface Props {
    hero: HeroInPlay | null | undefined
    heroArtUrl: string | null
    heroName: string
    health: number | null | undefined
    active?: boolean
    opacity?: boolean
    onClick?: () => void
}

const props = withDefaults(defineProps<Props>(), {
    active: false,
    opacity: false,
    onClick: undefined
})

const imageError = ref(false)

const activeClasses = computed(() => {
    const classes: string[] = ['border-gray-700']
    if (props.opacity) {
        classes.push('opacity-50')
    }
    return classes.join(' ')
})

const onImageError = () => {
    imageError.value = true
}

const handleClick = () => {
    if (props.onClick) {
        props.onClick()
    }
}
</script>

<template>
    <div class="game-card border-2 border-gray-900 bg-gray-300 text-gray-900 rounded-xl flex-1 flex flex-col p-1" :class="active_classes">
        <div class="text-wrap">
            <span v-if="compact" class="text-xs">{{ makeInitials(displayName) }}</span>
            <span v-else>{{ displayName }}</span>
        </div>
        <div class="flex-1">
            <div v-if="!compact" class="mt-2">
                <div>{{ card.description }}</div>
            </div>
        </div>
        <div class="flex flex-row justify-between" :class="compact ? 'text-xs' : ''">
            <div>{{ card.attack }} | {{ card.health }}</div>
            <div v-if="!in_lane" class="mr-1">{{ card.cost }}</div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Card } from '../../types/card'
import type { CardInPlay } from '../../types/game'
import { makeInitials } from '../../utils'

interface Props {
    card: Card | CardInPlay
    compact?: boolean
    in_lane?: boolean
    active?: boolean
}

const props = withDefaults(defineProps<Props>(), {
    compact: false,
    in_lane: false,
    active: false
})

// Convert template_slug to display name for CardInPlay, or use name for Card
const displayName = computed(() => {
    // If it's a Card type (has name property)
    if ('name' in props.card) {
        return props.card.name
    }
    // It must be CardInPlay type
    return (props.card as CardInPlay).template_slug
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase())
})

const active_classes = computed(() => {

    const classes: string[] = []

    if (props.in_lane && 'exhausted' in props.card && props.card.exhausted) {
        classes.push('bg-gray-400/20')
        classes.push('border-gray-900')
    }

    if (props.active) {
        classes.push('!border-yellow-500')
    }

    return classes.join(' ')
})
</script>

<style scoped>
.game-card {
    width: 100%;
    height: 100%;
    aspect-ratio: 5 / 7;
}
</style>
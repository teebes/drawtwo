<template>
    <div class="game-card border-2 border-gray-900 bg-gray-200 text-gray-900 rounded-xl flex-1 flex flex-col p-1 shadow-xl/30 shadow-white" :class="active_classes">
        <div class="text-xs text-wrap">
            <span v-if="compact">{{ makeInitials(displayName) }}</span>
            <span v-else>{{ displayName }}</span>
        </div>
        <div class="flex-1"></div>
        <div class="text-xs flex flex-row justify-between">
            <div>{{ card.attack }} | {{ card.health }}</div>
            <div v-if="!in_lane">{{ card.cost }}</div>
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
    // If it's a CardInPlay type (has template_slug property)
    if ('template_slug' in props.card) {
        return props.card.template_slug
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase())
    }
    // Fallback
    return 'Unknown Card'
})

const active_classes = computed(() => {

    const classes: string[] = []

    if (props.in_lane && 'exhausted' in props.card && props.card.exhausted) {
        classes.push('bg-gray-400/20')
        classes.push('border-gray-900')
    }

    if (props.active) {
        classes.push('!border-purple-500')
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
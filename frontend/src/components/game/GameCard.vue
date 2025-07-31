<template>
    <div class="game-card border-2 border-gray-500 bg-gray-800 rounded-xl flex-1 flex flex-col box-border p-1">
        <div class="text-ts text-wrap">
            <span v-if="compact">{{ makeInitials(displayName) }}</span>
            <span v-else>{{ displayName }}</span>
        </div>
        <div class="flex-1"></div>
        <div class="text-xs flex flex-row justify-between">
            <div>{{ card.attack }} | {{ card.health }}</div>
            <div>{{ card.cost }}</div>
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
}

const props = withDefaults(defineProps<Props>(), {
    compact: false
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
</script>

<style scoped>
.game-card {
    width: 100%;
    height: 100%;
    aspect-ratio: 5 / 7;
}
</style>
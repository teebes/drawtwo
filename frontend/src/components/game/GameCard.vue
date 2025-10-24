<template>
    <div class="game-card border-2 border-gray-900 bg-gray-300 text-gray-900 rounded-xl flex-1 flex flex-col p-1 relative" :class="active_classes">
        <!-- Taunt indicator -->
        <div v-if="hasTaunt" class="absolute -top-1 -right-1 w-5 h-5 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold" title="Taunt">
            🛡️
        </div>
        <div class="text-wrap break-words leading-tight" :class="compact ? 'text-[0.65rem]' : ''">
            <span>{{ displayName }}</span>
        </div>
        <div class="flex-1">
            <div v-if="!compact" class="mt-2">
                <div>{{ card.description }}</div>
            </div>
        </div>
        <div class="flex flex-row justify-between" :class="compact ? 'text-xs' : ''">
            <div>{{ card.attack }} | {{ card.health }}</div>
            <div v-if="!in_lane && displayCost !== null" class="mr-1">{{ displayCost }}</div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Card } from '../../types/card'
import type { CardInPlay, Creature } from '../../types/game'

interface Props {
    card: Card | CardInPlay | Creature
    compact?: boolean
    in_lane?: boolean
    active?: boolean
}

const props = withDefaults(defineProps<Props>(), {
    compact: false,
    in_lane: false,
    active: false
})

// Convert template_slug to display name for CardInPlay, or use name for Card/Creature
const displayName = computed(() => {
    // All types have name property now
    if ('name' in props.card) {
        return props.card.name
    }
    // Fallback for CardInPlay with template_slug
    if ('template_slug' in props.card) {
        return (props.card as CardInPlay).template_slug
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (l: string) => l.toUpperCase())
    }
    return 'Unknown'
})

const displayCost = computed(() => {
    // Only CardInPlay has cost, Creatures don't show cost
    if ('cost' in props.card) {
        return props.card.cost
    }
    return null
})

const hasTaunt = computed(() => {
    // Check if card has taunt trait
    if ('traits' in props.card && Array.isArray(props.card.traits)) {
        return props.card.traits.some((trait: any) => trait.type === 'taunt')
    }
    return false
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

    // Add special border for taunt creatures
    if (hasTaunt.value && props.in_lane) {
        classes.push('!border-blue-500')
        classes.push('!border-4')
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
<template>
    <div class="game-card border-2 border-gray-900 bg-gray-300 text-gray-900 rounded-xl flex-1 relative overflow-visible" :class="active_classes">
        <!-- Trait indicator (only one shown, priority order) -->
        <!-- Stealth indicator -->
        <div v-if="hasStealth" :class="['absolute bg-white text-white rounded-full flex items-center justify-center font-bold z-10 border border-gray-900 shadow-lg', badgeSizeClasses, badgePositionClasses.top, badgePositionClasses.left, badgeTextSizeClasses]" title="Stealth">
            👁️
        </div>
        <!-- Unique indicator -->
        <div v-else-if="hasUnique" :class="['absolute bg-white text-white rounded-full flex items-center justify-center font-bold z-10 border border-gray-900 shadow-lg', badgeSizeClasses, badgePositionClasses.top, badgePositionClasses.left, badgeTextSizeClasses]" title="Unique">
            ⭐
        </div>
        <!-- Taunt indicator -->
        <div v-else-if="hasTaunt" :class="['absolute bg-white text-gray-900 rounded-full flex items-center justify-center font-bold z-10 border border-gray-900 shadow-lg', badgeSizeClasses, badgePositionClasses.top, badgePositionClasses.left, badgeTextSizeClasses]" title="Taunt">
            🛡️
        </div>
        <!-- Charge indicator -->
        <div v-else-if="hasCharge" :class="['absolute bg-white text-white rounded-full flex items-center justify-center font-bold z-10 border border-gray-900 shadow-lg', badgeSizeClasses, badgePositionClasses.top, badgePositionClasses.left, badgeTextSizeClasses]" title="Charge">
            ⚔️
        </div>
        <!-- Deathrattle indicator -->
        <div v-else-if="hasDeathrattle" :class="['absolute bg-white text-white rounded-full flex items-center justify-center font-bold z-10 border border-gray-900 shadow-lg', badgeSizeClasses, badgePositionClasses.top, badgePositionClasses.left, badgeTextSizeClasses]" title="Deathrattle">
            💀
        </div>
        <!-- Battlecry indicator -->
        <div v-else-if="hasBattlecry" :class="['absolute bg-white text-white rounded-full flex items-center justify-center font-bold z-10 border border-gray-900 shadow-lg', badgeSizeClasses, badgePositionClasses.top, badgePositionClasses.left, badgeTextSizeClasses]" title="Battlecry">
            📣
        </div>

        <!-- Card Art (now fills whole card) -->
        <img
            :src="cardArtUrl"
            :alt="`${displayName} artwork`"
            class="absolute inset-0 w-full h-full object-cover rounded-[0.625rem]"
            @error="onImageError"
        />

        <!-- Attack Badge (lower left corner, extends beyond) -->
        <div v-if="!isSpell" :class="['card-badge bg-red-600', badgeSizeClasses, badgePositionClasses.bottom, badgePositionClasses.left, badgeFontClasses, badgeTextSizeClasses]">
            {{ card.attack }}
        </div>

        <!-- Health Badge (lower right corner, extends beyond) -->
        <div v-if="!isSpell" :class="['card-badge bg-green-600', badgeSizeClasses, badgePositionClasses.bottom, badgePositionClasses.right, badgeFontClasses, badgeTextSizeClasses]">
            {{ card.health }}
        </div>

        <!-- Cost Badge (upper right corner, only when in hand, extends beyond) -->
        <!-- absolute -top-3 -right-3 bg-blue-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold text-lg border-2 border-gray-900 z-20 shadow-lg -->
        <div v-if="!in_lane && displayCost !== null" :class="['card-badge bg-blue-600', badgeSizeClasses, badgePositionClasses.top, badgePositionClasses.right, badgeFontClasses, badgeTextSizeClasses]">
            {{ displayCost }}
        </div>

        <!-- Exhausted overlay -->
        <div v-if="props.in_lane && 'exhausted' in props.card && props.card.exhausted"
             class="absolute inset-0 bg-gray-900/70 z-10 pointer-events-none">
        </div>

    </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
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

const imageError = ref(false)

const cardArtUrl = computed(() => {

    // If image failed to load, use placeholder
    if (imageError.value) {
        return '/card_backs/placeholder.svg'
    }

    // Check if card has art_url (user-uploaded art)
    if ('art_url' in props.card && props.card.art_url) {
        return props.card.art_url
    }

    // Default fallback for other titles without custom art
    return '/card_backs/placeholder.svg'
})

const onImageError = () => {
    imageError.value = true
}

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

// Determine if this is a spell (spells don't show attack/health)
const isSpell = computed(() => {
    // Check if card has a card_type property indicating it's a spell
    if ('card_type' in props.card && props.card.card_type === 'spell') {
        return true
    }
    // Check if both attack and health are 0 (heuristic for spells)
    if (props.card.attack === 0 && props.card.health === 0) {
        return true
    }
    return false
})

const hasStealth = computed(() => {
    // Check if card has stealth trait
    if ('traits' in props.card && Array.isArray(props.card.traits)) {
        return props.card.traits.some((trait: any) => trait.type === 'stealth')
    }
    return false
})

const hasUnique = computed(() => {
    // Check if card has unique trait
    if ('traits' in props.card && Array.isArray(props.card.traits)) {
        return props.card.traits.some((trait: any) => trait.type === 'unique')
    }
    return false
})

const hasTaunt = computed(() => {
    // Check if card has taunt trait
    if ('traits' in props.card && Array.isArray(props.card.traits)) {
        return props.card.traits.some((trait: any) => trait.type === 'taunt')
    }
    return false
})

const hasCharge = computed(() => {
    // Check if card has charge trait
    if ('traits' in props.card && Array.isArray(props.card.traits)) {
        return props.card.traits.some((trait: any) => trait.type === 'charge')
    }
    return false
})

const hasDeathrattle = computed(() => {
    // Check if card has deathrattle trait
    if ('traits' in props.card && Array.isArray(props.card.traits)) {
        return props.card.traits.some((trait: any) => trait.type === 'deathrattle')
    }
    return false
})

const hasBattlecry = computed(() => {
    // Check if card has battlecry trait
    if ('traits' in props.card && Array.isArray(props.card.traits)) {
        return props.card.traits.some((trait: any) => trait.type === 'battlecry')
    }
    return false
})

const active_classes = computed(() => {

    const classes: string[] = []

    if (props.active) {
        classes.push('!border-yellow-500')
    }

    // Add special styling for stealth creatures
    if (hasStealth.value && props.in_lane) {
        classes.push('!border-purple-500')
        classes.push('opacity-70')
    }

    // Add special border for taunt creatures
    if (hasTaunt.value && props.in_lane) {
        classes.push('!border-blue-500')
        classes.push('!border-4')
    }

    return classes.join(' ')
})

const badgeSizeClasses = computed(() => {
    return props.compact ? 'w-5 h-5' : 'w-10 h-10'
})

const badgePositionClasses = computed(() => {
    if (props.compact) {
        return {
            top: '-top-1',
            bottom: '-bottom-1',
            left: '-left-1',
            right: '-right-1'
        }
    } else {
        return {
            top: '-top-3',
            bottom: '-bottom-3',
            left: '-left-3',
            right: '-right-3'
        }
    }
})

const badgeFontClasses = computed(() => {
    return props.compact ? '' : 'font-bold'
})

const badgeTextSizeClasses = computed(() => {
    return props.compact ? 'text-xs' : 'text-base'
})
</script>

<style scoped>
.game-card {
    width: 100%;
    height: 100%;
    aspect-ratio: 5 / 7;
}

.card-badge {
    @apply absolute text-white rounded-full flex items-center justify-center border border-gray-900 z-20 shadow-lg;

}
</style>
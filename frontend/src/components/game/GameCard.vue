<template>
    <div class="game-card border-2 border-gray-900 bg-gray-300 text-gray-900 rounded-xl relative" :class="active_classes">
        <!-- Trait indicator (only one shown, with a separate in-play priority) -->
        <div
            v-if="visibleTraitBadge"
            :class="['card-badge bg-white', visibleTraitBadge.textClass, badgeSizeClasses, badgePositionClasses.top, badgePositionClasses.left, badgeFontClasses, badgeTextSizeClasses]"
            :title="visibleTraitBadge.title"
        >
            {{ visibleTraitBadge.glyph }}
        </div>

        <div v-if="details" class="card-name absolute bg-black/80 text-white px-8 py-2 flex items-center justify-center gap-2 z-[15] text-lg font-bold">
            {{ card.name }}
        </div>

        <div v-if="details && card.description" class="absolute bottom-3 left-3 right-3 p-3 bg-black/80 rounded-xl text-xs text-white z-[15]">
            {{ card.description }}
        </div>

        <!-- Card Art (now fills whole card) -->
        <img
            :src="cardArtUrl"
            :alt="`${displayName}`"
            class="absolute w-full h-full object-cover rounded-xl"
            @error="onImageError"
        />

        <!-- Attack Badge (lower left corner, extends beyond) -->
        <div v-if="!isSpell" :class="['card-badge bg-red-500', badgeSizeClasses, badgePositionClasses.bottom, badgePositionClasses.left, badgeFontClasses, badgeTextSizeClasses]">
            {{ card.attack }}
        </div>

        <!-- Health Badge (lower right corner, extends beyond) -->
        <div v-if="!isSpell" :class="['card-badge bg-green-500', badgeSizeClasses, badgePositionClasses.bottom, badgePositionClasses.right, badgeFontClasses, badgeTextSizeClasses]">
            {{ card.health }}
        </div>

        <!-- Cost Badge (upper right corner, only when in hand, extends beyond) -->
        <div v-if="!isInPlay && displayCost !== null" :class="['card-badge bg-secondary-500', badgeSizeClasses, badgePositionClasses.top, badgePositionClasses.right, badgeFontClasses, badgeTextSizeClasses]">
            {{ displayCost }}
        </div>

        <!-- Exhausted overlay -->
        <div v-if="isInPlay && 'exhausted' in props.card && props.card.exhausted"
             class="absolute top-0 left-0 right-0 bottom-0 z-index-10 bg-gray-900/70 rounded-lg">
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
    details?: boolean
}

const props = withDefaults(defineProps<Props>(), {
    compact: false,
    in_lane: false,
    active: false,
    details: false
})

const imageError = ref(false)

interface TraitBadge {
    type: string
    glyph: string
    title: string
    textClass: string
}

const cardTraitBadges: TraitBadge[] = [
    { type: 'stealth', glyph: '👁️', title: 'Stealth', textClass: 'text-white' },
    { type: 'taunt', glyph: '🛡️', title: 'Taunt', textClass: 'text-gray-900' },
    { type: 'deathrattle', glyph: '💀', title: 'Deathrattle', textClass: 'text-white' },
    { type: 'battlecry', glyph: '📣', title: 'Battlecry', textClass: 'text-white' },
    { type: 'ranged', glyph: '🏹', title: 'Ranged', textClass: 'text-white' },
    { type: 'charge', glyph: '⚔️', title: 'Charge', textClass: 'text-white' },
    { type: 'unique', glyph: '⭐', title: 'Unique', textClass: 'text-white' }
]

const inPlayTraitBadges: TraitBadge[] = [
    { type: 'taunt', glyph: '🛡️', title: 'Taunt', textClass: 'text-gray-900' },
    { type: 'deathrattle', glyph: '💀', title: 'Deathrattle', textClass: 'text-white' },
    { type: 'triggered', glyph: '⚡️', title: 'Triggered', textClass: 'text-white' },
    { type: 'stealth', glyph: '👁️', title: 'Stealth', textClass: 'text-white' },
    { type: 'unique', glyph: '⭐', title: 'Unique', textClass: 'text-white' }
]

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
    // Prefer explicit card type information when it is available.
    if ('card_type' in props.card) {
        return props.card.card_type === 'spell'
    }
    // A zero-health creature retained briefly for its damage animation is still a creature.
    if (props.in_lane || 'creature_id' in props.card) {
        return false
    }
    // Check if both attack and health are 0 (heuristic for spells)
    if (props.card.attack === 0 && props.card.health === 0) {
        return true
    }
    return false
})

const traitTypes = computed(() => {
    const traits = Array.isArray(props.card.traits) ? props.card.traits : []
    return new Set(traits.map(trait => trait.type))
})

const isInPlay = computed(() => {
    return props.in_lane || 'creature_id' in props.card
})

const visibleTraitBadge = computed(() => {
    const priority = isInPlay.value ? inPlayTraitBadges : cardTraitBadges
    return priority.find(badge => traitTypes.value.has(badge.type)) ?? null
})

const hasStealth = computed(() => {
    return traitTypes.value.has('stealth')
})

const active_classes = computed(() => {

    const classes: string[] = []

    if (props.active) {
        classes.push('!border-primary-500')
    }

    // Add special styling for stealth creatures
    if (hasStealth.value && isInPlay.value) {
        classes.push('!border-purple-500')
        classes.push('opacity-70')
    }

    return classes.join(' ')
})

const badgeSizeClasses = computed(() => {
    return props.compact ? 'w-5 h-5' : 'w-8 h-8'
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
    return props.compact ? 'text-xs' : 'text-sm'
})
</script>

<style scoped>
.game-card {
    /* Use aspect-ratio as primary constraint - card will size from parent's width OR height */
    aspect-ratio: 5 / 7;
    /* If parent sets width, height will compute from ratio. If parent sets height, width will compute. */
    /* If parent sets neither, max-width/max-height ensure we fill available space while maintaining ratio */
    max-width: 100%;
    max-height: 100%;
}

.card-badge {
    @apply absolute text-white rounded-full flex items-center justify-center border border-gray-900 z-20 shadow-lg;
}

.card-name {
    /* Extend slightly to cover parent's border gap */
    left: -2px;
    right: -2px;
    border-radius: 0.75rem 0.75rem 0 0;
    top: -2px;
}
</style>

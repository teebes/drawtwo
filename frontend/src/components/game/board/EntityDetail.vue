<template>
    <div class="flex-1 flex flex-col">
        <!-- Entity Display -->
        <div class="flex flex-1 justify-center items-center">
            <div class="flex h-72 my-4 w-full">
                <div class="p-1 mx-auto">
                    <!-- Display Card or Creature -->
                    <GameCard v-if="displayCard" :card="displayCard" />

                    <!-- Display Hero -->
                    <div v-else-if="entityType === 'hero' && hero"
                         class="border-2 border-gray-900 bg-gray-300 text-gray-900 rounded-xl flex flex-col p-4 w-48">
                        <div class="text-xl font-bold mb-2">{{ hero.name }}</div>
                        <div class="flex-1 text-sm">Hero Power</div>
                        <div class="text-lg mt-2">Health: {{ hero.health }}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Action Section -->
        <div class="text-center w-full border-t border-gray-700 py-4">
            <div class="text-lg mb-4">{{ entityName }}</div>

            <!-- Error Message -->
            <div v-if="errorMessage" class="text-red-400 text-sm mb-4">
                {{ errorMessage }}
            </div>

            <!-- Available Actions -->
            <div class="flex flex-col space-y-2 px-4">
                <!-- Only show action buttons for owned entities -->
                <template v-if="isOwned">
                    <!-- Place on Board (Creature Cards Only) -->
                    <button
                        v-if="entityType === 'card' && card && card.card_type === 'creature'"
                        @click="handlePlaceCreature"
                        :disabled="!canPlayCard"
                        class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:opacity-50 text-white rounded-lg transition-colors"
                    >
                        Place on Board
                    </button>

                    <!-- Cast Spell (Spell Cards Only) -->
                    <button
                        v-if="entityType === 'card' && card && card.card_type === 'spell'"
                        @click="handleCastSpell"
                        :disabled="!canPlayCard"
                        class="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:opacity-50 text-white rounded-lg transition-colors"
                    >
                        {{ requiresTarget(card) ? 'Cast Spell (Select Target)' : 'Cast Spell' }}
                    </button>

                    <!-- Attack (Creatures on Board) -->
                    <button
                        v-if="entityType === 'creature' && creature"
                        @click="handleAttack"
                        :disabled="!canAttack"
                        class="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:opacity-50 text-white rounded-lg transition-colors"
                    >
                        Attack
                    </button>

                    <!-- Use Hero Power -->
                    <button
                        v-if="entityType === 'hero' && hero"
                        @click="handleUseHero"
                        :disabled="!canUseHero"
                        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:opacity-50 text-white rounded-lg transition-colors"
                    >
                        Use Hero Power
                    </button>
                </template>

                <!-- Close Button (always visible) -->
                <button
                    @click="emit('close')"
                    class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
                >
                    Close
                </button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CardInPlay, Creature, HeroInPlay } from '@/types/game'
import { useGameStore } from '@/stores/game'
import GameCard from '../GameCard.vue'

interface Props {
    entityType: 'card' | 'creature' | 'hero'
    entityId: string
    isOwned: boolean  // Whether this entity belongs to the current player
    card?: CardInPlay | null
    creature?: Creature | null
    hero?: HeroInPlay | null
}

const props = defineProps<Props>()
const gameStore = useGameStore()

const emit = defineEmits<{
    'close': []
    'place-creature': [cardId: string]
    'cast-spell': [cardId: string]
    'attack': [creatureId: string]
    'use-hero': [heroId: string]
}>()

// Display card (for both card in hand and creature on board)
const displayCard = computed(() => {
    if (props.entityType === 'card' && props.card) {
        return props.card
    }
    if (props.entityType === 'creature' && props.creature) {
        // Convert Creature to CardInPlay format for display
        return {
            card_id: props.creature.card_id,
            template_slug: props.creature.name,
            name: props.creature.name,
            description: props.creature.description,
            attack: props.creature.attack,
            health: props.creature.health,
            cost: 0, // Creatures on board don't have cost
            traits: props.creature.traits,
            exhausted: props.creature.exhausted,
            card_type: 'creature' as const
        }
    }
    return null
})

const entityName = computed(() => {
    if (props.card) return props.card.name || 'Card'
    if (props.creature) return props.creature.name || 'Creature'
    if (props.hero) return props.hero.name || 'Hero'
    return 'Entity'
})

const canPlayCard = computed(() => {
    if (props.entityType !== 'card' || !props.card) return false

    const availableEnergy = gameStore.ownEnergy
    if (props.card.cost > availableEnergy) return false

    // Check turn and phase
    if (gameStore.gameState.active !== gameStore.currentViewer) return false
    if (gameStore.gameState.phase !== 'main') return false

    return true
})

const errorMessage = computed(() => {
    if (props.entityType === 'card' && props.card) {
        const availableEnergy = gameStore.ownEnergy
        if (props.card.cost > availableEnergy) {
            return `Not enough energy (need ${props.card.cost}, have ${availableEnergy})`
        }
    }

    if (props.entityType === 'creature' && props.creature) {
        if (props.creature.exhausted) {
            return 'Creature is exhausted'
        }
    }

    if (props.entityType === 'hero' && props.hero) {
        if (!gameStore.canUseHero) {
            return 'Cannot use hero power'
        }
    }

    return null
})

const canAttack = computed(() => {
    if (props.entityType !== 'creature' || !props.creature) return false

    // Can't control opponent's creatures
    if (!props.isOwned) return false

    if (props.creature.exhausted) return false

    // Check turn and phase
    if (gameStore.gameState.active !== gameStore.currentViewer) return false
    if (gameStore.gameState.phase !== 'main') return false

    return true
})

const canUseHero = computed(() => {
    // Can't control opponent's hero
    if (!props.isOwned) return false

    return gameStore.canUseHero
})

function requiresTarget(card: CardInPlay): boolean {
    const traits = card.traits || []

    // Check if it's a spell with targeting
    if (card.card_type === 'spell') {
        for (const trait of traits) {
            const actions = trait.actions || []
            for (const action of actions) {
                if (action.action === 'damage') {
                    return true
                }
            }
        }
    }

    return false
}

function handlePlaceCreature() {
    if (props.entityType === 'card' && canPlayCard.value) {
        emit('place-creature', props.entityId)
    }
}

function handleCastSpell() {
    if (props.entityType === 'card' && canPlayCard.value) {
        emit('cast-spell', props.entityId)
    }
}

function handleAttack() {
    if (props.entityType === 'creature' && canAttack.value) {
        emit('attack', props.entityId)
    }
}

function handleUseHero() {
    if (props.entityType === 'hero' && canUseHero.value) {
        emit('use-hero', props.entityId)
    }
}
</script>

<template>
    <div class="placement-selector flex-1 min-h-0">
        <!-- Selected Card Display -->
        <div class="placement-source flex min-h-0 items-center justify-center overflow-hidden py-4">
            <div v-if="cardId && card" class="placement-source-card">
                <GameCard class="h-full w-full" :card="card"/>
            </div>
        </div>

        <template v-if="gameState.winner === 'none'">
            <div class="placement-prompt flex items-center justify-center border-y border-gray-700 px-4 text-center">
                Choose where to place this creature
            </div>

            <!-- Board Placement Area -->
            <div class="placement-lane flex w-full items-center overflow-x-auto border-b border-gray-700 bg-gray-800">
                <!-- If the card can be played -->
                <div v-if="canPlaceCreature" class="flex flex-row h-24 items-center mx-auto">
                    <!-- Show placement zones with current board creatures -->
                    <template v-if="ownBoard && ownBoard.length > 0">
                        <!-- Place at beginning -->
                        <PlacementZone
                            :position="0"
                            @placement-clicked="handlePlacement"
                        />

                        <!-- Interleave creatures with placement zones -->
                        <template v-for="(creature, index) in ownBoard" :key="`creature-${creature.creature_id}`">
                            <div class="p-1 w-16">
                                <GameCard v-if="creature"
                                        class="flex-grow-0"
                                        :card="creature"
                                        :title-slug="props.titleSlug"
                                        compact in_lane />
                            </div>
                            <PlacementZone
                                :position="index + 1"
                                @placement-clicked="handlePlacement"
                            />
                        </template>
                    </template>

                    <!-- Place in center if no creatures -->
                    <template v-else>
                        <PlacementZone
                            :position="0"
                            @placement-clicked="handlePlacement"
                        />
                    </template>
                </div>

                <!-- Cannot place creature message -->
                <div v-else class="flex flex-row w-full h-24 items-center justify-center"
                            @click="emit('close')">
                    <div class="text-red-400 text-center cursor-pointer">
                        <div class="text-lg">Cannot place this creature</div>
                        <div class="text-sm opacity-75">
                            Insufficient energy
                            [<span class="mx-1">{{ ownEnergy }}</span> / <span class="mx-1">{{ card?.cost }}</span>]
                        </div>
                        <div class="text-xs opacity-50 mt-2">Click to close</div>
                    </div>
                </div>
            </div>
        </template>

        <div
            v-if="card"
            class="placement-details flex min-h-0 flex-col items-center justify-center px-6 text-center">
            <div class="text-lg" :class="{ 'mb-4': card.description }">
                {{ card.name }}
            </div>
            <div v-if="card.description">
                {{ card.description }}
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { GameState, Creature } from '@/types/game'
import { useGameStore } from '@/stores/game'
import GameCard from '../GameCard.vue'
import PlacementZone from '../PlacementZone.vue'

interface Props {
    gameState: GameState
    cardId: string | null
    ownBoard: Creature[] | undefined
    ownEnergy: number | undefined
}

const props = defineProps<Props>()
const gameStore = useGameStore()

const emit = defineEmits<{
    'close': []
    'placement-selected': [{ card_id: string; position: number; allowedTargets: Array<'card' | 'hero' | 'any'>; targetScope: 'enemy' | 'friendly' }]
}>()

const card = computed(() => {
    if (!props.cardId) return null
    return props.gameState.cards[props.cardId]
})

const handlePlacement = (position: number) => {
    if (!props.cardId || !card.value) return

    // If the card has a battlecry that needs a target, emit with target info
    if (requiresTargetOnPlay(card.value)) {
        const allowedTargets = getAllowedTargets(card.value)
        const targetScope = getTargetScope(card.value)
        emit('placement-selected', {
            card_id: props.cardId,
            position,
            allowedTargets,
            targetScope
        })
        return
    }

    // Otherwise play immediately
    gameStore.playCard(props.cardId, position)
    emit('close')
}

const canPlaceCreature = computed(() => {
    if (!props.cardId || !props.ownEnergy) return false

    const cardToPlace = card.value
    if (!cardToPlace) return false
    if (cardToPlace.card_type !== 'creature') return false
    if (cardToPlace.cost > props.ownEnergy) return false

    return true
})

function requiresTargetOnPlay(card: any): boolean {
    const traits = card.traits || []
    const battlecry = traits.find((t: any) => t.type === 'battlecry')
    if (!battlecry) return false
    return hasTargetingActions([battlecry])
}

function hasTargetingActions(traits: any[]): boolean {
    for (const trait of traits) {
        const actions = trait.actions || []
        for (const action of actions) {
            if (
                (action.action === 'damage' || action.action === 'heal' || action.action === 'remove' || action.action === 'silence' || action.action === 'buff') &&
                action.scope !== 'all'
            ) {
                if (action.action === 'buff' && action.target === 'hero') {
                    continue
                }
                return true
            }
        }
    }
    return false
}

function getAllowedTargets(card: any): Array<'card' | 'hero' | 'any'> {
    const allowed = new Set<'card' | 'hero' | 'any'>()
    const traits = card.traits || []
    const battlecry = traits.find((t: any) => t.type === 'battlecry')
    if (!battlecry) return ['any']

    for (const action of battlecry.actions || []) {
        if (action.action === 'damage') {
            if (action.target === 'creature' || action.target === 'enemy' || action.target === 'friendly') {
                allowed.add('card')
            }
            if (action.target === 'hero' || action.target === 'enemy' || action.target === 'friendly') {
                allowed.add('hero')
            }
        }
        if (action.action === 'heal') {
            if (action.target === 'creature' || action.target === 'friendly') {
                allowed.add('card')
            }
            if (action.target === 'hero' || action.target === 'friendly') {
                allowed.add('hero')
            }
        }
        if (action.action === 'remove' || action.action === 'silence') {
            // Remove and silence target enemy creatures only
            allowed.add('card')
        }
        if (action.action === 'buff') {
            if (action.target === 'creature' || action.target === 'friendly') {
                allowed.add('card')
            }
            if (action.target === 'hero' || action.target === 'friendly') {
                allowed.add('hero')
            }
        }
    }

    if (allowed.size === 0) allowed.add('any')
    return Array.from(allowed)
}

function getTargetScope(card: any): 'enemy' | 'friendly' {
    const traits = card.traits || []
    const battlecry = traits.find((t: any) => t.type === 'battlecry')
    if (!battlecry) return 'enemy'

    for (const action of battlecry.actions || []) {
        // Heal actions target friendly units
        if (action.action === 'heal') {
            return 'friendly'
        }
        // Buff actions target friendly units
        if (action.action === 'buff') {
            return 'friendly'
        }
        if (action.action === 'damage') {
            if (action.target === 'friendly' || action.target === 'self') {
                return 'friendly'
            }
            return 'enemy'
        }
        // Remove actions target enemies
        if (action.action === 'remove' || action.action === 'silence') {
            return 'enemy'
        }
    }

    return 'enemy'
}
</script>

<style scoped>
.placement-selector {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows:
        calc(4.2rem + 1px)
        minmax(0, 1fr)
        3.5rem
        minmax(0, 1fr)
        calc(4.2rem + 1px)
        6rem;
}

.placement-source {
    grid-column: 1;
    grid-row: 1 / 3;
}

.placement-source-card {
    aspect-ratio: 5 / 7;
    height: min(16.8rem, calc(100% - 2rem));
    max-width: calc(100% - 2rem);
}

.placement-prompt {
    grid-column: 1;
    grid-row: 3;
}

.placement-lane {
    grid-column: 1;
    grid-row: 4;
}

.placement-details {
    grid-column: 1;
    grid-row: 5 / 7;
}
</style>

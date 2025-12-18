<template>
    <div class="flex-1 flex flex-col">
        <!-- Board Placement Area -->
        <template v-if="gameState.winner === 'none'">
            <div class="flex w-full bg-gray-800 border-b border-t border-gray-700 py-8 overflow-x-auto">
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

            <div class="text-center w-full border-b border-gray-700 py-2">
                Choose where to place this creature
            </div>
        </template>

        <!-- Selected Card Display -->
        <div class="flex flex-1 justify-center items-center">
            <div v-if="cardId && card" class="flex h-72 my-4">
                <div class="p-1 w-48 mx-auto">
                    <GameCard class="" :card="card"/>
                </div>
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
                (action.action === 'damage' || action.action === 'heal' || action.action === 'remove' || action.action === 'buff') &&
                action.scope !== 'all'
            ) {
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
            if (action.target === 'creature' || action.target === 'enemy') {
                allowed.add('card')
            }
            if (action.target === 'hero' || action.target === 'enemy') {
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
        if (action.action === 'remove') {
            // Remove targets enemy creatures only
            allowed.add('card')
        }
        if (action.action === 'buff') {
            // Buff targets friendly creatures only
            allowed.add('card')
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
        // Damage actions target enemies
        if (action.action === 'damage') {
            return 'enemy'
        }
        // Remove actions target enemies
        if (action.action === 'remove') {
            return 'enemy'
        }
    }

    return 'enemy'
}
</script>

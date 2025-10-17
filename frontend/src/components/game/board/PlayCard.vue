<template>
    <div class="flex-1 flex flex-col">


        <!-- Current Board with Placement Zones -->
        <template v-if="gameState.winner === 'none'">
            <div class="flex w-full bg-gray-800 border-b border-t border-gray-700 py-8 overflow-x-auto">
                <!-- If the card can be played -->
                <div v-if="canPlayCard" class="flex flex-row h-24 items-center mx-auto">
                    <!-- Show placement zones with current board cards -->
                    <template v-if="ownBoard && ownBoard.length > 0">
                        <!-- Place at beginning -->
                        <PlacementZone
                            :position="0"
                            @placement-clicked="handleCardPlacement"
                        />

                        <!-- Interleave creatures with placement zones -->
                        <template v-for="(creature, index) in ownBoard" :key="`creature-${creature.creature_id}`">
                            <div class="p-1 h-24">
                                <GameCard v-if="creature"
                                        class="flex-grow-0"
                                        :card="creature"
                                        compact in_lane />
                            </div>
                            <PlacementZone
                                :position="index + 1"
                                @placement-clicked="handleCardPlacement"
                            />
                        </template>
                    </template>

                    <!-- Place in center if no cards -->
                    <template v-else>
                        <PlacementZone
                            :position="0"
                            @placement-clicked="handleCardPlacement"
                        />
                    </template>
                </div>

                <!-- Cannot play card message -->
                <div v-else class="flex flex-row w-full h-24 items-center justify-center"
                            @click="emit('close-overlay')">
                    <div class="text-red-400 text-center">
                        <div class="text-lg">Cannot play this card</div>
                        <div class="text-sm opacity-75">
                            Insufficient energy
                            [<span class="mx-1">{{ ownEnergy }}</span> / <span class="mx-1">{{ card?.cost }}</span>]
                        </div>
                    </div>
                </div>
            </div>

            <div class="text-center w-full border-b border-gray-700 py-2">Place the card on the board</div>
        </template>

        <!-- Selected Hand Card Display -->
        <div class="flex flex-1 justify-center items-center">
            <div v-if="selectedHandCard && getCard(selectedHandCard)" class="flex h-72 my-4">
                <div class="p-1 mx-auto">
                    <GameCard class="" :card="getCard(selectedHandCard)!"/>
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
    selectedHandCard: string | null
    ownBoard: Creature[] | undefined
    ownEnergy: number | undefined
}

const props = defineProps<Props>()
const gameStore = useGameStore()

const emit = defineEmits<{
    'close-overlay': []
    'target-required': [{ card_id: string; position: number; allowedTargets: Array<'card' | 'hero' | 'any'> }]
}>()

const card = computed(() => {
    if (!props.selectedHandCard) return null
    return getCard(props.selectedHandCard)
})

const getCard = (card_id: string) => {
    return props.gameState.cards[card_id]
}

const handleCardPlacement = (position: number) => {
    if (!props.selectedHandCard) return

    // If the card has a battlecry that needs a target, emit target-required
    const playedCard = getCard(props.selectedHandCard)
    if (playedCard && requiresTargetOnPlay(playedCard)) {
        const allowedTargets = getAllowedTargets(playedCard)
        emit('target-required', { card_id: props.selectedHandCard, position, allowedTargets })
        return
    }

    // Otherwise send immediately
    gameStore.playCard(props.selectedHandCard, position)

    // Close the overlay
    emit('close-overlay')
}

const canPlayCard = computed(() => {
    if (!props.selectedHandCard) return false
    if (!props.ownEnergy) return false

    const card = getCard(props.selectedHandCard)

    if (!card) return false

    if (card.cost <= props.ownEnergy ) return true

    return false
})

function requiresTargetOnPlay(card: any): boolean {
    // Spells always may require targets depending on actions; treat similar to battlecry
    const traits = card.traits || []
    const battlecry = traits.find((t: any) => t.type === 'battlecry')
    if (!battlecry) {
        // Some spells might encode their behaviors as battlecry-equivalent via battlecry type
        return card.card_type === 'spell' && hasTargetingActions(traits)
    }
    return hasTargetingActions([battlecry])
}

function hasTargetingActions(traits: any[]): boolean {
    for (const trait of traits) {
        const actions = trait.actions || []
        for (const action of actions) {
            if (action.action === 'damage') {
                // damage typically needs a target (hero or creature or enemy)
                return true
            }
        }
    }
    return false
}

function getAllowedTargets(card: any): Array<'card' | 'hero' | 'any'> {
    const allowed = new Set<'card' | 'hero' | 'any'>()
    const traits = card.traits || []
    const consider = traits.find((t: any) => t.type === 'battlecry') || { actions: [] }
    for (const action of consider.actions || []) {
        if (action.action === 'damage') {
            if (action.target === 'creature' || action.target === 'enemy') {
                allowed.add('card')
            }
            if (action.target === 'hero' || action.target === 'enemy') {
                allowed.add('hero')
            }
        }
    }
    if (allowed.size === 0) allowed.add('any')
    return Array.from(allowed)
}
</script>
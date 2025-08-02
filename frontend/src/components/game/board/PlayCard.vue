<template>
    <div class="flex-1 flex flex-col">

        <!-- Selected Hand Card Display -->
        <div class="flex flex-1 justify-center items-center">
            <div v-if="selectedHandCard && getCard(selectedHandCard)" class="flex h-72 my-4">
                <div class="p-1 mx-auto">
                    <GameCard class="" :card="getCard(selectedHandCard)!"/>
                </div>
            </div>
        </div>

        <div class="text-center w-full border-t border-gray-700 py-2">Place the card on the board</div>

        <!-- Current Board with Placement Zones -->
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

                    <!-- Interleave cards with placement zones -->
                    <template v-for="(card, index) in ownBoard" :key="`card-${card.card_id}`">
                        <div class="p-1 h-24">
                            <GameCard v-if="card"
                                      class="flex-grow-0"
                                      :card="card"
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


    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { GameState, CardInPlay } from '@/types/game'
import { useGameStore } from '@/stores/game'
import GameCard from '../GameCard.vue'
import PlacementZone from '../PlacementZone.vue'

interface Props {
    gameState: GameState | null
    selectedHandCard: string | null
    ownBoard: CardInPlay[] | undefined
    ownEnergy: number | undefined
}

const props = defineProps<Props>()
const gameStore = useGameStore()

console.log(props.ownBoard)

const emit = defineEmits<{
    'close-overlay': []
}>()

const card = computed(() => {
    if (!props.selectedHandCard) return null
    return getCard(props.selectedHandCard)
})

const getCard = (card_id: string) => {
    return props.gameState?.cards[card_id]
}

const handleCardPlacement = (position: number) => {
    if (!props.selectedHandCard) return

    console.log('Playing card', props.selectedHandCard, 'at position', position)

    // Use store action directly instead of emitting to parent
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
</script>
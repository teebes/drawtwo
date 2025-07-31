<template>
    <div class="flex-1 flex flex-col">
        <!-- Card Details-->
        <div class="card-details flex-1 border-b border-gray-700 overflow-y-auto p-4">
            <div>{{ card?.name }}</div>
            <div>{{ card?.description }}</div>
        </div>

        <!-- Selected Hand Card Display -->
        <div v-if="selectedHandCard && getCard(selectedHandCard)" class="flex h-80 my-4">
            <div class="p-1 mx-auto">
                <GameCard
                class=""
                    :card="getCard(selectedHandCard)!"
                    compact
                />
            </div>
        </div>

        <!-- Current Board with Placement Zones -->
        <div class="flex w-full bg-gray-800 border-b border-t border-gray-700 py-8">
            <!-- If the card can be played -->
            <div v-if="canPlayCard" class="flex flex-row w-full h-24 items-center justify-center">
                <!-- Show placement zones with current board cards -->
                <template v-if="ownBoard && ownBoard.length > 0">
                    <!-- Place at beginning -->
                    <PlacementZone
                        :position="0"
                        @placement-clicked="handleCardPlacement"
                    />

                    <!-- Interleave cards with placement zones -->
                    <template v-for="(card_id, index) in ownBoard" :key="`card-${card_id}`">
                        <div class="p-1">
                            <GameCard v-if="getCard(card_id)"
                                      class="flex-grow-0"
                                      :card="getCard(card_id)!"
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
import type { GameState } from '../../../types/game'
import GameCard from '../GameCard.vue'
import PlacementZone from '../PlacementZone.vue'

interface Props {
    gameState: GameState | null
    selectedHandCard: string | null
    ownBoard: string[] | undefined
    ownEnergy: number | undefined
}

const props = defineProps<Props>()

const emit = defineEmits<{
    'card-placement': [cardId: string, position: number]
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

    emit('card-placement', props.selectedHandCard, position)
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
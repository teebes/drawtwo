<template>
    <div class="flex-1 flex flex-col">

        <!-- Selected Card Display -->
        <div class="flex flex-1 justify-center items-center">
            <div v-if="card" class="flex h-72 my-4 w-full">
                <div class="p-1 mx-auto">
                    <GameCard :card="card"
                    />
                </div>
            </div>
        </div>

        <div class="text-center w-full border-t border-gray-700 py-2">Select Target</div>

        <!-- Opponent Board -->
        <div class="flex w-full bg-gray-800 border-b border-t border-gray-700 py-8 overflow-x-auto">

            <!-- If the card can be played -->
            <div v-if="canPlayCard" class="flex flex-row w-full h-24 mx-auto">
                <div v-for="card in opposingBoard" :key="card.card_id" class="p-1">
                    <GameCard v-if="card"
                              class="flex-grow-0"
                              :card="card"
                              compact in_lane
                              @click="handleCardClick(card.card_id)"
                              />
                </div>
            </div>

            <!-- Cannot play card message -->
            <div v-else class="flex flex-row w-full h-24 items-center justify-center"
                        @click="emit('close-overlay')">
                <div class="text-red-400 text-center">
                    <div class="text-lg">Cannot use this card</div>
                    <div class="text-sm opacity-75">
                        Card is Exhausted
                    </div>
                </div>
            </div>
        </div>

        <!-- Opponent Hero-->
        <div class="flex w-full justify-center cursor-pointer"
             @click="handleHeroClick">
            <div class="flex flex-col h-24 items-center justify-center border-gray-700">
                <div>{{ opposingHero?.name }}</div>
                <div>{{ opposingHero?.health }}</div>
            </div>
        </div>


    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { GameState, CardInPlay, HeroInPlay } from '@/types/game'
import { useGameStore } from '@/stores/game'
import GameCard from '../GameCard.vue'

interface Props {
    gameState: GameState | null
    card: CardInPlay | null
    ownBoard: CardInPlay[] | []
    opposingBoard: CardInPlay[] | []
    opposingHero: HeroInPlay | null
    opposingHeroInitials: string | null
}

const props = defineProps<Props>()
const gameStore = useGameStore()

const emit = defineEmits<{
    'close-overlay': []
}>()


const canPlayCard = computed(() => {
    if (!props.card) return false

    if (!props.card) return false

    if (!props.card.exhausted) return true

    return false
})

const handleHeroClick = () => {
    if (!props.opposingHero || !props.card) return

    // Use store action directly instead of emitting to parent
    gameStore.useCardOnHero(props.card.card_id, props.opposingHero.hero_id)

    // Close the overlay
    emit('close-overlay')
}

const handleCardClick = (cardId: string) => {
    if (!props.card) return
    gameStore.useCardOnCard(props.card.card_id, cardId)
    emit('close-overlay')
}
</script>
<template>
    <div class="flex-1 flex flex-col">

        <template v-if="gameState.winner === 'none'">
            <!-- Opponent Hero-->
            <div v-if="!noplay_reason"
                class="flex w-full justify-center border-gray-700 border-b"
                :class="canSelectHeroTarget ? 'cursor-pointer' : 'opacity-50 pointer-events-none'"
                @click="canSelectHeroTarget && handleHeroClick()">
                <div class="flex flex-col h-24 items-center justify-center border-gray-700">
                    <div>{{ opposingHero?.name }}</div>
                    <div>{{ opposingHero?.health }}</div>
                </div>
            </div>

            <!-- Opponent Board -->
            <div class="flex w-full bg-gray-800 border-b border-gray-700 py-8 overflow-x-auto">

                <!-- If interactions are allowed (selection mode always allows) -->
                <div v-if="canInteract" class="flex flex-row w-full h-24 mx-auto">
                    <div v-for="card in opposingBoard" :key="card.card_id" class="p-1">
                        <GameCard v-if="card"
                                class="flex-grow-0"
                                :card="card"
                                compact in_lane
                                :class="canSelectCardTargets ? 'cursor-pointer' : 'opacity-50 pointer-events-none'"
                                @click="canSelectCardTargets && handleCardClick(card.card_id)"
                                />
                    </div>
                </div>

                <!-- Cannot play card message -->
                <div v-else-if="noplay_reason" class="flex flex-row w-full h-24 items-center justify-center"
                            @click="emit('close-overlay')">
                    <div class="text-red-400 text-center">
                        <div class="text-lg">Cannot use this card</div>
                        <div class="text-sm opacity-75">
                            {{ noplay_reason }}
                        </div>
                    </div>
                </div>
            </div>

            <div v-if="!noplay_reason" class="text-center w-full border-b border-gray-700 py-2">Select Target</div>
        </template>

        <!-- Selected Card Display -->
        <div class="flex flex-1 justify-center items-center">
            <div v-if="card" class="flex h-72 my-4 w-full">
                <div class="p-1 mx-auto">
                    <GameCard :card="card"
                    />
                </div>
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
    gameState: GameState
    card: CardInPlay | null
    ownBoard: CardInPlay[] | []
    opposingBoard: CardInPlay[] | []
    opposingHero: HeroInPlay | null
    opposingHeroInitials: string | null
    mode?: 'use' | 'select'
    allowedTargetTypes?: Array<'card' | 'hero' | 'any'>
}

const props = defineProps<Props>()
const gameStore = useGameStore()

const emit = defineEmits<{
    'close-overlay': []
    'target-selected': [{ target_type: 'card' | 'hero'; target_id: string }]
}>()

const isSelectionMode = computed(() => props.mode === 'select')

const canInteract = computed(() => canPlayCard.value)

const canSelectCardTargets = computed(() => {
    const types = props.allowedTargetTypes || ['card', 'hero', 'any']
    return types.includes('card') || types.includes('any')
})

const canSelectHeroTarget = computed(() => {
    const types = props.allowedTargetTypes || ['card', 'hero', 'any']
    return types.includes('hero') || types.includes('any')
})

const canPlayCard = computed(() => {
    return !noplay_reason.value
})

// Similar to canPlayCard except it returns a message indicating why it can't
// be played if it cannot, and null if it can
const noplay_reason = computed(() => {
    if (!props.card) return 'No card selected'

    if (props.card.card_type === 'spell') {
        const availableEnergy = gameStore.gameState.mana_pool[props.gameState.active] - gameStore.gameState.mana_used[props.gameState.active]
        if (props.card.cost > availableEnergy) return 'Not enough energy'
    }

    if (props.card.card_type === 'minion'&& props.card.exhausted) return 'Card is exhausted'

    return null
})

const handleHeroClick = () => {
    if (!props.opposingHero || !props.card) return

    if (isSelectionMode.value) {
        emit('target-selected', { target_type: 'hero', target_id: props.opposingHero.hero_id })
        emit('close-overlay')
        return
    }
    gameStore.useCardOnHero(props.card.card_id, props.opposingHero.hero_id)
    emit('close-overlay')
}

const handleCardClick = (cardId: string) => {
    if (!props.card) return
    if (isSelectionMode.value) {
        emit('target-selected', { target_type: 'card', target_id: cardId })
        emit('close-overlay')
        return
    }
    gameStore.useCardOnCard(props.card.card_id, cardId)
    emit('close-overlay')
}
</script>
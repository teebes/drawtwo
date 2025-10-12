<template>
    <div class="flex-1 flex flex-col">

        <template v-if="gameState.winner === 'none'">
            <!-- Opponent Hero -->
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
                <div v-if="canInteract" class="flex flex-row h-24 mx-auto">
                    <div v-for="cardInLane in opposingBoard" :key="cardInLane.card_id" class="p-1">
                        <GameCard v-if="cardInLane"
                                class="flex-grow-0"
                                :card="cardInLane"
                                compact in_lane
                                :class="canSelectCardTargets ? 'cursor-pointer' : 'opacity-50 pointer-events-none'"
                                @click="canSelectCardTargets && handleCardClick(cardInLane.card_id)"
                                />
                    </div>
                </div>

                <!-- Cannot use message -->
                <div v-else-if="noplay_reason" class="flex flex-row w-full h-24 items-center justify-center"
                            @click="emit('close-overlay')">
                    <div class="text-red-400 text-center">
                        <div class="text-lg">Cannot use</div>
                        <div class="text-sm opacity-75">
                            {{ noplay_reason }}
                        </div>
                    </div>
                </div>
            </div>

            <div v-if="!noplay_reason" class="text-center w-full border-b border-gray-700 py-2">Select Target</div>
        </template>

        <!-- Selected Initiator Display (card only for now) -->
        <div class="flex flex-1 justify-center items-center">
            <div v-if="initiator.type === 'card' && card" class="flex h-72 my-4 w-full">
                <div class="p-1 mx-auto">
                    <GameCard :card="card" />
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

interface Initiator {
    type: 'card' | 'hero'
    id: string
}

interface Props {
    gameState: GameState
    initiator: Initiator
    card?: CardInPlay | null
    ownBoard?: CardInPlay[] | []
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

const canInteract = computed(() => noplay_reason.value === null)

const canSelectCardTargets = computed(() => {
    const types = props.allowedTargetTypes || ['card', 'hero', 'any']
    return types.includes('card') || types.includes('any')
})

const canSelectHeroTarget = computed(() => {
    const types = props.allowedTargetTypes || ['card', 'hero', 'any']
    return types.includes('hero') || types.includes('any')
})

// Similar to canInteract except it returns a message string if cannot use
const noplay_reason = computed(() => {
    // For card initiator, reuse existing card rules
    if (props.initiator.type === 'card') {
        if (!props.card) return 'No card selected'

        if (props.card.card_type === 'spell') {
            const availableEnergy = gameStore.gameState.mana_pool[props.gameState.active] - gameStore.gameState.mana_used[props.gameState.active]
            if (props.card.cost > availableEnergy) return 'Not enough energy'
        }

        if (props.card.card_type === 'creature' && props.card.exhausted) return 'Card is exhausted'
        return null
    }

    // For hero initiator, basic turn/phase validation
    const viewer = gameStore.currentViewer
    if (!viewer) return 'No viewer'
    if (props.gameState.active !== viewer) return 'Not your turn'
    if (props.gameState.phase !== 'main') return 'Not in main phase'

    // Check if hero is exhausted
    const hero = props.gameState.heroes[viewer]
    if (hero?.exhausted) return 'Hero is exhausted'

    return null
})

const handleHeroClick = () => {
    if (!props.opposingHero) return

    if (isSelectionMode.value) {
        emit('target-selected', { target_type: 'hero', target_id: props.opposingHero.hero_id })
        emit('close-overlay')
        return
    }

    if (props.initiator.type === 'card') {
        if (!props.card) return
        gameStore.useCardOnHero(props.card.card_id, props.opposingHero.hero_id)
        emit('close-overlay')
        return
    }

    // Hero initiator
    gameStore.useHeroOnHero(props.initiator.id, props.opposingHero.hero_id)
    emit('close-overlay')
}

const handleCardClick = (cardId: string) => {
    if (isSelectionMode.value) {
        emit('target-selected', { target_type: 'card', target_id: cardId })
        emit('close-overlay')
        return
    }

    if (props.initiator.type === 'card') {
        if (!props.card) return
        gameStore.useCardOnCard(props.card.card_id, cardId)
        emit('close-overlay')
        return
    }

    // Hero initiator
    gameStore.useHeroOnCard(props.initiator.id, cardId)
    emit('close-overlay')
}
</script>

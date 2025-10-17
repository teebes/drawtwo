<template>
    <div class="flex-1 flex flex-col">

        <!-- Error State -->
        <template v-if="errorMessage">
            <div class="flex flex-col flex-1 items-center justify-center"
                 @click="emit('cancelled')">
                <div class="text-red-400 text-center cursor-pointer">
                    <div class="text-lg">Cannot Select Target</div>
                    <div class="text-sm opacity-75 mt-2">
                        {{ errorMessage }}
                    </div>
                    <div class="text-xs opacity-50 mt-4">
                        Click to close
                    </div>
                </div>
            </div>
        </template>

        <!-- Target Selection State -->
        <template v-else>
            <!-- Opponent Hero -->
            <div v-if="canTargetHero"
                class="flex w-full justify-center border-gray-700 border-b cursor-pointer hover:bg-gray-700"
                @click="handleHeroClick">
                <div class="flex flex-col h-24 items-center justify-center">
                    <div>{{ opposingHero?.name }}</div>
                    <div>{{ opposingHero?.health }} HP</div>
                </div>
            </div>
            <div v-else-if="opposingHero"
                class="flex w-full justify-center border-gray-700 border-b opacity-30">
                <div class="flex flex-col h-24 items-center justify-center">
                    <div>{{ opposingHero?.name }}</div>
                    <div>{{ opposingHero?.health }} HP</div>
                </div>
            </div>

            <!-- Opponent Board -->
            <div class="flex w-full bg-gray-800 border-b border-gray-700 py-8 overflow-x-auto">
                <div v-if="opposingBoard.length > 0" class="flex flex-row h-24 mx-auto">
                    <div v-for="creature in opposingBoard" :key="creature.creature_id" class="p-1">
                        <GameCard
                            class="flex-grow-0"
                            :card="creature"
                            compact
                            in_lane
                            :class="canTargetCreature ? 'cursor-pointer hover:scale-105 transition-transform' : 'opacity-30'"
                            @click="canTargetCreature && handleCreatureClick(creature.creature_id)"
                        />
                    </div>
                </div>
                <div v-else class="flex flex-row w-full h-24 items-center justify-center text-gray-500">
                    No creatures on board
                </div>
            </div>

            <!-- Header -->
            <div class="text-center w-full border-b border-gray-700 py-2">
                {{ title }}
            </div>

            <!-- Source Card Display (if provided) -->
            <div class="flex flex-1 justify-center items-center">
                <div v-if="sourceCard" class="flex h-72 my-4 w-full">
                    <div class="p-1 mx-auto">
                        <GameCard :card="sourceCard" />
                    </div>
                </div>
            </div>
        </template>

    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CardInPlay, Creature, HeroInPlay } from '@/types/game'
import GameCard from '../GameCard.vue'

type TargetType = 'creature' | 'hero' | 'both'

interface Props {
    opposingBoard: Creature[]
    opposingHero: HeroInPlay | null
    allowedTargetTypes: TargetType
    sourceCard?: CardInPlay | Creature | null
    errorMessage?: string | null
    title?: string
}

const props = withDefaults(defineProps<Props>(), {
    sourceCard: null,
    errorMessage: null,
    title: 'Select Target'
})

const emit = defineEmits<{
    'target-selected': [{ target_type: 'creature' | 'hero'; target_id: string }]
    'cancelled': []
}>()

const canTargetCreature = computed(() => {
    return props.allowedTargetTypes === 'creature' || props.allowedTargetTypes === 'both'
})

const canTargetHero = computed(() => {
    return props.allowedTargetTypes === 'hero' || props.allowedTargetTypes === 'both'
})

const handleHeroClick = () => {
    if (!props.opposingHero || !canTargetHero.value) return
    emit('target-selected', {
        target_type: 'hero',
        target_id: props.opposingHero.hero_id
    })
}

const handleCreatureClick = (creatureId: string) => {
    if (!canTargetCreature.value) return
    emit('target-selected', {
        target_type: 'creature',
        target_id: creatureId
    })
}
</script>

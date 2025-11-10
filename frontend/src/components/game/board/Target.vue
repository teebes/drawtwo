<template>
    <div class="flex-1 flex flex-col">

        <!-- Target Selection State -->

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

        <template v-else>

            <!-- Opponent Hero (if targeting enemies) -->
            <div v-if="showOpposingHero && canTargetHero && opposingHero"
                class="flex w-full justify-center border-gray-700 border-b cursor-pointer hover:bg-gray-700"
                @click="handleHeroClick(opposingHero.hero_id)">
                <div class="flex flex-col h-24 items-center justify-center">
                    <div class="text-xs opacity-75">Opponent</div>
                    <div>{{ opposingHero?.name }}</div>
                    <div>{{ opposingHero?.health }} HP</div>
                </div>
            </div>
            <div v-else-if="showOpposingHero && opposingHero"
                class="flex w-full justify-center border-gray-700 border-b opacity-30">
                <div class="flex flex-col h-24 items-center justify-center">
                    <div class="text-xs opacity-75">Opponent</div>
                    <div>{{ opposingHero?.name }}</div>
                    <div>{{ opposingHero?.health }} HP</div>
                </div>
            </div>

            <!-- Opponent Board (if targeting enemies) -->
            <div v-if="showOpposingBoard" class="flex w-full bg-gray-800 border-b border-gray-700 py-8 overflow-x-auto">
                <div v-if="opposingBoard.length > 0" class="flex flex-row h-24 mx-auto">
                    <div v-for="creature in opposingBoard" :key="creature.creature_id" class="p-1">
                        <GameCard
                            class="flex-grow-0"
                            :card="creature"
                            compact
                            in_lane
                            :class="canTargetSpecificCreature(creature) ? 'cursor-pointer hover:scale-105 transition-transform' : 'opacity-30'"
                            @click="canTargetSpecificCreature(creature) && handleCreatureClick(creature.creature_id)"
                        />
                    </div>
                </div>
                <div v-else class="flex flex-row w-full h-24 items-center justify-center text-gray-500">
                    No enemy creatures
                </div>
            </div>

            <!-- Own Board (if targeting friendly) -->
            <div v-if="showOwnBoard" class="flex w-full bg-gray-800 border-b border-gray-700 py-8 overflow-x-auto">
                <div v-if="ownBoard && ownBoard.length > 0" class="flex flex-row h-24 mx-auto">
                    <div v-for="creature in ownBoard" :key="creature.creature_id" class="p-1">
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
                    No friendly creatures
                </div>
            </div>

            <!-- Own Hero (if targeting friendly) -->
            <div v-if="showOwnHero && canTargetHero && ownHero"
                class="flex w-full justify-center border-gray-700 border-b cursor-pointer hover:bg-gray-700"
                @click="handleHeroClick(ownHero.hero_id)">
                <div class="flex flex-col h-24 items-center justify-center">
                    <div class="text-xs opacity-75">Your Hero</div>
                    <div>{{ ownHero?.name }}</div>
                    <div>{{ ownHero?.health }} HP</div>
                </div>
            </div>
            <div v-else-if="showOwnHero && ownHero"
                class="flex w-full justify-center border-gray-700 border-b opacity-30">
                <div class="flex flex-col h-24 items-center justify-center">
                    <div class="text-xs opacity-75">Your Hero</div>
                    <div>{{ ownHero?.name }}</div>
                    <div>{{ ownHero?.health }} HP</div>
                </div>
            </div>

            <!-- Header -->
            <div class="text-center w-full py-2">
                {{ title }}
            </div>

        </template>

        <!-- Source Card Display (if provided) -->
        <div class="flex flex-1 justify-center items-center border-t border-gray-700">
            <div v-if="sourceCard" class="flex h-72 my-4 w-full">
                <div class="p-1 mx-auto">
                    <GameCard :card="sourceCard" />
                </div>
            </div>
        </div>


    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CardInPlay, Creature, HeroInPlay } from '@/types/game'
import GameCard from '../GameCard.vue'

type TargetType = 'creature' | 'hero' | 'both'
type TargetScope = 'enemy' | 'friendly' | 'any'

interface Props {
    opposingBoard: Creature[]
    opposingHero: HeroInPlay | null
    ownBoard?: Creature[]
    ownHero?: HeroInPlay | null
    allowedTargetTypes: TargetType
    targetScope?: TargetScope  // Default to 'enemy' for backward compatibility
    sourceCard?: CardInPlay | Creature | null
    errorMessage?: string | null
    title?: string
}

const props = withDefaults(defineProps<Props>(), {
    ownBoard: () => [],
    ownHero: null,
    targetScope: 'enemy',
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
    // Cannot target hero if there are taunt creatures on the opposing board
    const baseCanTarget = props.allowedTargetTypes === 'hero' || props.allowedTargetTypes === 'both'

    // If targeting enemies, check for taunt creatures
    if (baseCanTarget && (props.targetScope === 'enemy' || props.targetScope === 'any')) {
        const hasTauntCreatures = props.opposingBoard.some(creature =>
            creature.traits?.some((trait: any) => trait.type === 'taunt')
        )
        if (hasTauntCreatures) {
            return false // Cannot target hero while taunt creatures exist
        }
    }

    return baseCanTarget
})

// Helper to check if a creature has taunt
const hasTaunt = (creature: Creature): boolean => {
    return creature.traits?.some((trait: any) => trait.type === 'taunt') ?? false
}

// Get taunt creatures from the opposing board
const tauntCreatures = computed(() => {
    if (props.targetScope === 'enemy' || props.targetScope === 'any') {
        return props.opposingBoard.filter(creature => hasTaunt(creature))
    }
    return []
})

// Check if a specific creature can be targeted
const canTargetSpecificCreature = (creature: Creature): boolean => {
    if (!canTargetCreature.value) return false

    // If there are taunt creatures and this isn't one of them, can't target it
    if (tauntCreatures.value.length > 0) {
        return hasTaunt(creature)
    }

    return true
}

// Determine which boards/heroes to show based on target scope
const showOpposingBoard = computed(() => {
    return props.targetScope === 'enemy' || props.targetScope === 'any'
})

const showOpposingHero = computed(() => {
    return props.targetScope === 'enemy' || props.targetScope === 'any'
})

const showOwnBoard = computed(() => {
    return props.targetScope === 'friendly' || props.targetScope === 'any'
})

const showOwnHero = computed(() => {
    return props.targetScope === 'friendly' || props.targetScope === 'any'
})

const handleHeroClick = (heroId: string) => {
    if (!canTargetHero.value) return
    emit('target-selected', {
        target_type: 'hero',
        target_id: heroId
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

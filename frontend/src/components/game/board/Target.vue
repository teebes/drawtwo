<template>
    <div class="target-selector flex-1 min-h-0">
        <!-- Error State -->
        <div
            v-if="errorMessage"
            class="target-error flex flex-col items-center justify-center"
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

        <template v-else>
            <!-- Source card, description, or prompt occupies the non-targeted side. -->
            <div
                class="target-source flex min-h-0 flex-col justify-center overflow-y-auto"
                :class="[
                    sourceRegionClass,
                    { 'border-t border-gray-700 bg-gray-900': targetScope === 'any' }
                ]">
                <template v-if="targetScope === 'any'">
                    <div class="target-source-any-content grid h-full min-w-0 items-center px-3 py-2">
                        <div class="flex min-w-0 justify-center">
                            <div v-if="sourceCard" class="w-14 shrink-0">
                                <GameCard :card="sourceCard" compact />
                            </div>
                        </div>
                        <div aria-hidden="true"></div>
                        <div class="min-w-0 flex-1">
                            <div class="truncate text-sm font-semibold">
                                {{ sourceCard?.name ?? title }}
                            </div>
                            <div
                                v-if="sourceSummaryDescription"
                                class="target-source-summary-description mt-1 text-xs leading-snug text-gray-400">
                                {{ sourceSummaryDescription }}
                            </div>
                        </div>
                    </div>
                </template>
                <template v-else>
                    <div
                        v-if="sourceHero"
                        class="flex min-h-0 flex-1 flex-col items-center justify-center px-6 py-5 w-full">
                        <div class="max-w-[280px] text-center">
                            <div class="text-base text-gray-400">{{ title }}</div>
                            <div
                                v-if="sourceDescription"
                                class="mt-3 text-base leading-relaxed text-gray-100">
                                {{ sourceDescription }}
                            </div>
                        </div>
                    </div>
                    <div v-else-if="sourceCard" class="flex min-h-0 flex-1 items-center py-4 w-full">
                        <div
                            class="p-1 mx-auto"
                            :class="targetScope === 'friendly' ? 'w-[7.8rem]' : 'w-48'">
                            <GameCard :card="sourceCard" />
                        </div>
                    </div>
                    <div
                        v-else-if="sourceDescription"
                        class="w-full px-6 text-base leading-relaxed"
                        :class="sourceDescriptionAlignmentClass">
                        <div class="mx-auto flex w-full max-w-[250px] flex-col gap-4">
                            <div class="text-center text-gray-400">{{ title }}:</div>
                            <div class="text-left text-gray-100">{{ sourceDescription }}</div>
                        </div>
                    </div>
                    <div v-else class="text-center w-full py-2">
                        {{ title }}
                    </div>

                    <div v-if="sourceCard" class="shrink-0 text-center border-t border-gray-700 py-4 px-4">
                        <div class="text-lg mb-4">{{ sourceCard.name }}</div>
                        <div>{{ sourceCard.description }}</div>
                    </div>
                </template>
            </div>

            <!-- Opponent Hero (if targeting enemies) -->
            <button
                v-if="showOpposingHero && canTargetHero && opposingHero"
                type="button"
                class="target-opposing-hero flex h-24 w-24 justify-center cursor-pointer hover:bg-gray-700"
                :aria-label="`Opponent, ${opposingHero.name}, ${opposingHero.health} HP`"
                @click="handleHeroClick(opposingHero.hero_id)">
                <div class="h-24">
                    <Hero
                        class="pointer-events-none"
                        :hero="opposingHero"
                        :hero-art-url="opposingHero.art_url ?? null"
                        :hero-name="opposingHero.name"
                        :health="opposingHero.health"
                    />
                </div>
                <span
                    aria-hidden="true"
                    class="pointer-events-none absolute inset-0 z-30 border-x border-gray-700">
                </span>
            </button>
            <div
                v-else-if="showOpposingHero && opposingHero"
                class="target-opposing-hero flex h-24 w-24 justify-center opacity-30"
                role="button"
                aria-disabled="true"
                :aria-label="`Opponent, ${opposingHero.name}, ${opposingHero.health} HP, target unavailable`">
                <div class="h-24">
                    <Hero
                        class="pointer-events-none"
                        :hero="opposingHero"
                        :hero-art-url="opposingHero.art_url ?? null"
                        :hero-name="opposingHero.name"
                        :health="opposingHero.health"
                    />
                </div>
                <span
                    aria-hidden="true"
                    class="pointer-events-none absolute inset-0 z-30 border-x border-gray-700">
                </span>
            </div>

            <!-- Opponent Board (if targeting enemies) -->
            <div
                v-if="showOpposingBoard"
                class="target-opposing-board flex w-full items-center bg-gray-800 border-y border-gray-700 overflow-x-auto">
                <div v-if="opposingBoard.length > 0" class="lane flex flex-row h-24 mx-auto space-x-2">
                    <div
                        v-for="creature in opposingBoard"
                        :key="creature.creature_id"
                        class="w-14 shrink-0">
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
            <div
                v-if="showOwnBoard"
                class="target-own-board flex w-full items-center bg-gray-800 border-y border-gray-700 overflow-x-auto">
                <div v-if="ownBoard && ownBoard.length > 0" class="lane flex flex-row h-24 mx-auto space-x-2">
                    <div
                        v-for="creature in ownBoard"
                        :key="creature.creature_id"
                        class="w-14 shrink-0">
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
            <button
                v-if="showOwnHero && canTargetHero && ownHero"
                type="button"
                class="target-own-hero flex h-24 w-24 justify-center cursor-pointer hover:bg-gray-700"
                :class="{ 'target-own-hero--friendly': targetScope === 'friendly' }"
                :aria-label="`Your Hero, ${ownHero.name}, ${ownHero.health} HP`"
                @click="handleHeroClick(ownHero.hero_id)">
                <div class="h-24">
                    <Hero
                        class="pointer-events-none"
                        :hero="ownHero"
                        :hero-art-url="ownHero.art_url ?? null"
                        :hero-name="ownHero.name"
                        :health="ownHero.health"
                        :active="targetScope === 'any'"
                    />
                </div>
                <span
                    aria-hidden="true"
                    class="pointer-events-none absolute inset-0 z-30 border-2 border-gray-700">
                </span>
            </button>
            <div
                v-else-if="showOwnHero && ownHero"
                class="target-own-hero flex h-24 w-24 justify-center opacity-30"
                :class="{ 'target-own-hero--friendly': targetScope === 'friendly' }"
                role="button"
                aria-disabled="true"
                :aria-label="`Your Hero, ${ownHero.name}, ${ownHero.health} HP, target unavailable`">
                <div class="h-24">
                    <Hero
                        class="pointer-events-none"
                        :hero="ownHero"
                        :hero-art-url="ownHero.art_url ?? null"
                        :hero-name="ownHero.name"
                        :health="ownHero.health"
                        :active="targetScope === 'any'"
                    />
                </div>
                <span
                    aria-hidden="true"
                    class="pointer-events-none absolute inset-0 z-30 border-2 border-gray-700">
                </span>
            </div>
        </template>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CardInPlay, Creature, HeroInPlay } from '@/types/game'
import GameCard from '../GameCard.vue'
import Hero from './Hero.vue'

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
    sourceHero?: HeroInPlay | null
    sourceDescription?: string | null
    errorMessage?: string | null
    title?: string
    bypassTaunt?: boolean
}

const props = withDefaults(defineProps<Props>(), {
    ownBoard: () => [],
    ownHero: null,
    targetScope: 'enemy',
    sourceCard: null,
    sourceHero: null,
    sourceDescription: null,
    errorMessage: null,
    title: 'Select Target',
    bypassTaunt: false
})

const emit = defineEmits<{
    'target-selected': [{ target_type: 'creature' | 'hero'; target_id: string }]
    'cancelled': []
}>()

const canTargetCreature = computed(() => {
    return props.allowedTargetTypes === 'creature' || props.allowedTargetTypes === 'both'
})

// Check if the source is a spell (spells are not affected by taunt)
const isSpellSource = computed(() => {
    if (props.bypassTaunt) return true
    return props.sourceCard && 'card_type' in props.sourceCard && props.sourceCard.card_type === 'spell'
})

const canTargetHero = computed(() => {
    // Cannot target hero if there are taunt creatures on the opposing board
    // BUT: Spells are NOT affected by taunt restrictions
    const baseCanTarget = props.allowedTargetTypes === 'hero' || props.allowedTargetTypes === 'both'

    // If targeting enemies, check for taunt creatures (only for non-spell sources)
    if (baseCanTarget && (props.targetScope === 'enemy' || props.targetScope === 'any') && !isSpellSource.value) {
        const hasTauntCreatures = props.opposingBoard.some(creature =>
            creature.traits?.some((trait: any) => trait.type === 'taunt')
        )
        if (hasTauntCreatures) {
            return false // Cannot target hero while taunt creatures exist (for creature attacks)
        }
    }

    return baseCanTarget
})

// Helper to check if a creature has taunt
const hasTaunt = (creature: Creature): boolean => {
    return creature.traits?.some((trait: any) => trait.type === 'taunt') ?? false
}

    // Helper to check if a creature has stealth
const hasStealth = (creature: Creature): boolean => {
    return creature.traits?.some((trait: any) => trait.type === 'stealth') ?? false
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

    // Stealth Check: Cannot target creatures with stealth
    if (hasStealth(creature)) {
        return false
    }

    // Taunt restrictions only apply to creature attacks, not spells
    // If the source is a spell, taunt doesn't restrict targeting
    if (isSpellSource.value) {
        return true
    }

    // If there are taunt creatures and this isn't one of them, can't target it
    // (This applies to creature attacks)
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

const sourceRegionClass = computed(() => {
    if (props.targetScope === 'friendly') return 'target-source--friendly'
    if (props.targetScope === 'enemy') return 'target-source--enemy'
    return 'target-source--any'
})

const sourceDescriptionAlignmentClass = computed(() => {
    return props.targetScope === 'friendly'
        ? 'mt-auto pb-[clamp(3rem,10vh,6rem)]'
        : 'mb-auto pt-[clamp(3rem,10vh,6rem)]'
})

const sourceSummaryDescription = computed(() => {
    return props.sourceCard?.description || props.sourceDescription
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

<style scoped>
.target-selector {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    /*
     * The compact targeting header gives its reclaimed height to the first
     * row, so a 6rem hero fits between the title and the enemy lane while the
     * lane itself stays at the same board coordinate.
     */
    grid-template-rows:
        6rem
        minmax(0, 1fr)
        3.5rem
        minmax(0, 1fr)
        calc(4.2rem + 1px)
        6rem;
}

.target-error {
    grid-column: 1;
    grid-row: 1 / -1;
}

.target-source {
    grid-column: 1;
}

.target-source--enemy {
    grid-row: 3 / 7;
}

.target-source--friendly {
    grid-row: 1 / 4;
}

.target-source--any {
    grid-row: 6;
    overflow: hidden;
    z-index: 5;
}

.target-source-any-content {
    grid-template-columns: minmax(0, 1fr) 6rem minmax(0, 1fr);
}

.target-source-summary-description {
    display: -webkit-box;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
}

.target-opposing-hero {
    align-self: end;
    grid-column: 1;
    grid-row: 1;
    justify-self: center;
    position: relative;
    z-index: 10;
}

.target-opposing-board {
    grid-column: 1;
    grid-row: 2;
}

.target-own-board {
    grid-column: 1;
    grid-row: 4;
}

.target-own-hero {
    align-self: start;
    grid-column: 1;
    grid-row: 5;
    justify-self: center;
    position: relative;
    z-index: 10;
}

.target-own-hero--friendly {
    align-self: center;
    grid-row: 5 / 7;
}
</style>

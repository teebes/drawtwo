<template>
    <div class="min-h-screen flex flex-row justify-center relative" v-if="!loading">

        <!-- Game Over Overlay -->
        <GameOverOverlay
            v-if="showingGameOver"
            :game-over="gameOver"
            :viewer="viewer"
            @close="showingGameOver = false" />

        <!-- Normal Mode -->
        <main v-if="!overlay" class="board flex-1 flex flex-col max-w-md w-full border-r border-l border-gray-700">

            <!-- Opponent Side -->
            <div class="side-b flex-1 flex flex-col">

                <!-- Header -->
                 <div class="h-24 flex flex-row justify-between border-b border-gray-700">
                    <!-- Enemy Hero-->
                    <div class="w-24 flex flex-col items-center justify-center border-r border-gray-700 cursor-pointer hover:bg-gray-700/50"
                         :class="{ 'bg-yellow-500/20': gameState.active === topSide }"
                         @click="handleClickOpposingHero">
                        <div class="text-xs text-center break-words leading-tight px-1">{{ opposingHeroName }}</div>
                        <div class="">{{ opposingHero?.health }}</div>
                    </div>

                    <!-- Recent Updates -->
                    <div class="flex flex-1 flex-col p-2 justify-center items-center cursor-pointer" @click="handleClickUpdates">
                        <Update v-if="displayUpdates.length > 0" :update="displayUpdates[displayUpdates.length - 1]" />
                    </div>

                    <!-- Menu -->
                    <div class="w-24 flex justify-center items-center text-center border-l border-gray-700">
                        <span class="inline-block cursor-pointer" @click="handleMenuClick">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-label="Menu" xmlns="http://www.w3.org/2000/svg">
                                <rect y="5" width="24" height="2" rx="1" fill="currentColor"/>
                                <rect y="11" width="24" height="2" rx="1" fill="currentColor"/>
                                <rect y="17" width="24" height="2" rx="1" fill="currentColor"/>
                            </svg>
                        </span>
                    </div>
                 </div>

                 <!-- Stats -->
                 <div class="flex flex-row justify-around border-b border-gray-700 p-2">
                    <div class="flex flex-col text-center">
                        <div>Deck</div>
                        <div>{{ opposingDeckSize }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div>Hand</div>
                        <div>{{ opposingHandSize }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div>Energy</div>
                        <div>{{ opposingEnergy }}/{{ opposingEnergyPool }}</div>
                    </div>
                 </div>

                 <!-- Opponent Board -->
                 <div class="opponent-board flex-1 flex flex-row bg-gray-800 items-center overflow-x-auto">
                    <div class="lane flex flex-row h-24 mx-auto">
                        <div v-for="creature in opposingBoard" :key="creature.creature_id" class="p-1">
                            <GameCard v-if="creature"
                                      class="flex-grow-0 cursor-pointer hover:scale-105 transition-transform"
                                      :card="creature"
                                      @click="handleClickOpposingCreature(creature.creature_id)"
                                      compact in_lane/>
                        </div>
                    </div>
                 </div>
            </div>

            <!-- Mid Section -->
            <div class="flex flex-row justify-between border-gray-700 border-t border-b min-h-14">
                <div class="flex items-center justify-center ml-2">
                    Turn {{ gameState.turn }} <span class="text-gray-400 ml-2">[ {{ gameState.phase }} ]</span>
                </div>
                <GameButton
                    v-if="gameState.winner === 'none'"
                    variant="secondary"
                    class="m-2"
                    @click="handleEndTurn">End Turn</GameButton>
                <div v-else class="flex items-center justify-center mr-4">{{ gameOver.winner }} wins!</div>
            </div>

            <!-- Viewer Side-->
            <div class="side-a flex-1 flex flex-col">
                <!-- Viewer Board-->
                <div class="viewer-board flex-1 flex flex-row bg-gray-800 items-center overflow-x-auto">
                    <div class="lane flex flex-row h-24 mx-auto">
                        <div v-for="creature in ownBoard" :key="creature.creature_id" class="p-1">
                            <GameCard v-if="creature"
                                      class="flex-grow-0 cursor-pointer hover:scale-105 transition-transform"
                                      :card="creature"
                                      @click="handleClickOwnCreature(creature.creature_id)"
                                      compact in_lane/>
                        </div>
                    </div>
                 </div>

                <!-- Stats -->
                 <div class="flex flex-row justify-around border-t border-gray-700 p-2">
                    <div class="flex flex-col text-center">
                        <div>Deck</div>
                        <div>{{ ownDeckSize }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div>Hand</div>
                        <div>{{ ownHandSize }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div>Energy</div>
                        <div>{{ ownEnergy }}/{{ ownEnergyPool }}</div>
                    </div>
                 </div>

                <!-- Footer -->
                <div class="h-24 flex flex-row border-t border-gray-700">
                    <!-- Viewer Hero -->
                    <div class="hero w-24 h-full border-r border-gray-700 flex flex-col items-center justify-center cursor-pointer hover:bg-gray-700/50"
                         :class="{
                           'bg-yellow-500/20': gameState.active === bottomSide,
                           'opacity-50': !canUseHero
                         }"
                         @click="handleClickOwnHero">
                        <div class="hero-name text-xs text-center break-words leading-tight px-1">{{ ownHeroName }}</div>
                        <div class="hero-health">{{ ownHero?.health }}</div>
                    </div>

                    <!-- Hand -->
                    <div class="hand overflow-x-auto flex flex-row">
                        <div v-for="card_id in ownHand" :key="card_id" class="p-1">
                            <GameCard v-if="get_card(card_id)"
                                      class="flex-grow-0 cursor-pointer hover:scale-105 transition-transform"
                                      :card="get_card(card_id)!"
                                      :active="isHandCardActive(card_id)"
                                      @click="handleClickHandCard(card_id)"
                                      compact />
                        </div>
                    </div>
                </div>
            </div>

        </main>

        <!-- Overlay Mode -->
         <main v-else class="board flex-1 flex flex-col max-w-md w-full border-r border-l border-gray-700">
            <!-- Header -->
            <OverlayHeader :text="overlayTitle" @close="closeOverlay" />

            <!-- Entity Detail Overlay -->
            <EntityDetail
                v-if="overlay === 'entity_detail' && selectedEntity"
                :entity-type="selectedEntity.type"
                :entity-id="selectedEntity.id"
                :is-owned="selectedEntity.isOwned ?? true"
                :card="selectedEntity.type === 'card' ? get_card(selectedEntity.id) : null"
                :creature="selectedEntity.type === 'creature' ? get_creature(selectedEntity.id) : null"
                :hero="selectedEntity.type === 'hero' ? getHero(selectedEntity.id) : null"
                @close="closeOverlay"
                @place-creature="handlePlaceCreature"
                @cast-spell="handleCastSpell"
                @attack="handleAttack"
                @use-hero="handleUseHero"
            />

            <!-- Creature Placement Overlay -->
            <PlaceCreature
                v-if="overlay === 'place_creature'"
                :game-state="gameState"
                :card-id="selectedCardId"
                :own-board="ownBoard"
                :own-energy="ownEnergy"
                @placement-selected="onPlacementSelected"
                @close="closeOverlay"
            />

            <!-- Target Selection Overlay -->
            <Target
                v-if="overlay === 'select_target' && targetingState"
                :opposing-board="opposingBoard"
                :opposing-hero="opposingHero"
                :own-board="ownBoard"
                :own-hero="ownHero"
                :allowed-target-types="targetingState.allowedTypes"
                :target-scope="targetingState.scope"
                :source-card="targetingState.sourceCard"
                :error-message="targetingState.errorMessage"
                :title="targetingState.title"
                @target-selected="onTargetSelected"
                @cancelled="closeOverlay"
            />

            <!-- Menu Overlay -->
            <div v-if="overlay === 'menu'">
                <div class="flex flex-col items-center justify-center space-y-8 my-8">
                    <div class="text-2xl cursor-pointer hover:text-gray-400" @click="handleClickUpdates">
                        Updates
                    </div>

                    <div v-if="canEditTitle" class="text-2xl cursor-pointer hover:text-gray-400" @click="handleClickDebug">
                        Debug
                    </div>

                    <div class="text-2xl">
                        <router-link :to="{ name: 'Title', params: { slug: titleStore.titleSlug } }"
                                     class="hover:text-gray-400">
                            Exit Game
                        </router-link>
                    </div>
                </div>
            </div>

            <!-- Updates Overlay -->
            <div v-if="overlay === 'updates'" class="flex-1 min-h-0">
                <div class="flex flex-col h-full border-gray-700 overflow-y-auto">
                    <div class="flex border-gray-700 items-center justify-center py-2" :class="{ 'border-b': update.type === 'update_end_turn' }"
                         v-for="update in displayUpdates" :key="update.timestamp">
                        <Update :update="update" />
                    </div>
                </div>
            </div>

            <!-- Debug Overlay -->
            <DebugOverlay v-if="overlay === 'debug'" :game-id="gameId" />

         </main>

        <!-- -->
    </div>

    <!-- Loading Screen -->
    <div class="min-h-screen flex flex-row justify-center" v-else>
        <div class="flex flex-col items-center justify-center">
            <div class="text-2xl font-bold">Loading...</div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { watch, computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import type { CardInPlay, Creature } from '../types/game'
import { useAuthStore } from '../stores/auth'
import { useTitleStore } from '../stores/title'
import { useGameStore } from '../stores/game'
import { storeToRefs } from 'pinia'

import GameCard from '../components/game/GameCard.vue'
import GameButton from '../components/ui/GameButton.vue'
// Board Components
import EntityDetail from '../components/game/board/EntityDetail.vue'
import PlaceCreature from '../components/game/board/PlaceCreature.vue'
import Target from '../components/game/board/Target.vue'
import GameOverOverlay from '../components/game/board/GameOverOverlay.vue'
import Update from '../components/game/board/Update.vue'
import OverlayHeader from '../components/game/board/OverlayHeader.vue'
import DebugOverlay from '../components/game/board/DebugOverlay.vue'

const route = useRoute()
const authStore = useAuthStore()
const titleStore = useTitleStore()
const gameStore = useGameStore()

// Get reactive refs from the store
const {
  loading,
  gameState,
  gameOver,
  viewer,
  ownHero,
  ownHeroName,
  ownHandSize,
  ownDeckSize,
  ownHand,
  ownEnergy,
  ownEnergyPool,
  ownBoard,
  opposingHero,
  opposingHeroName,
  opposingHandSize,
  opposingDeckSize,
  opposingEnergy,
  opposingEnergyPool,
  opposingBoard,
  topSide,
  bottomSide,
  displayUpdates,
  canUseHero
} = storeToRefs(gameStore)

// Overlay Types
type OverlayType = 'entity_detail' | 'place_creature' | 'select_target' | 'menu' | 'updates' | 'debug' | null

// Local UI state
const overlay = ref<OverlayType>(null)
const overlayTitle = ref<string>('')

// Entity selection state (for detail view)
interface SelectedEntity {
    type: 'card' | 'creature' | 'hero'
    id: string
    isOwned?: boolean  // Whether this entity belongs to the current player
}
const selectedEntity = ref<SelectedEntity | null>(null)

// Card selection for placement
const selectedCardId = ref<string | null>(null)

// Targeting state
interface TargetingState {
    sourceType: 'creature' | 'hero' | 'spell' | 'battlecry'
    sourceId: string
    allowedTypes: 'creature' | 'hero' | 'both'
    scope: 'enemy' | 'friendly' | 'any'
    sourceCard: CardInPlay | Creature | null
    errorMessage: string | null
    title: string
}
const targetingState = ref<TargetingState | null>(null)

// Pending play context when battlecry target is required
const pendingPlay = ref<{ card_id: string; position: number } | null>(null)

const showingGameOver = ref(false)

const title = computed(() => titleStore.currentTitle)

// Check if user can edit this title (for debug features)
const canEditTitle = computed(() => {
  return authStore.isAuthenticated &&
         title.value &&
         title.value.can_edit === true
})

// Game ID for debug overlay
const gameId = computed(() => route.params.game_id as string)

// Helper methods from store
const get_card = (card_id: string | number) => {
    return gameStore.getCard(String(card_id))
}

const get_creature = (creature_id: string) => {
    return gameStore.getCreature(String(creature_id))
}

const getHero = (hero_id: string) => {
    return gameState.value.heroes[hero_id]
}

const isHandCardActive = (card_id: string | number) => {
    return gameStore.isHandCardActive(String(card_id))
}

/* Click Handlers - Opening Entity Details or Initiating Actions */

// When clicking a card in hand (always owned by player)
const handleClickHandCard = (card_id: string) => {
    console.log('handleClickHandCard', card_id)
    const card = get_card(card_id)
    if (!card) return

    // If it's a spell that requires targeting, go directly to targeting
    if (card.card_type === 'spell' && requiresTarget(card)) {
        pendingPlay.value = { card_id, position: 0 }  // Set pendingPlay for spell casting
        targetingState.value = {
            sourceType: 'spell',
            sourceId: card_id,
            allowedTypes: convertAllowedTargets(getAllowedTargets(card)),
            scope: getSpellTargetScope(card),
            sourceCard: card,
            errorMessage: null,
            title: 'Cast Spell'
        }
        overlay.value = 'select_target'
        overlayTitle.value = 'Select Target'
        return
    }

    // Otherwise show entity detail (for creatures or non-targeting spells)
    selectedEntity.value = { type: 'card', id: card_id, isOwned: true }
    overlay.value = 'entity_detail'
    overlayTitle.value = 'Card Details'
}

// When clicking own creature on board - go directly to targeting
const handleClickOwnCreature = (creature_id: string) => {
    console.log('handleClickOwnCreature', creature_id)
    const creature = get_creature(creature_id)
    if (!creature) return

    targetingState.value = {
        sourceType: 'creature',
        sourceId: creature_id,
        allowedTypes: 'both',  // Creatures can attack both heroes and other creatures
        scope: 'enemy',
        sourceCard: creature,
        errorMessage: creature.exhausted ? 'Creature is exhausted' : null,
        title: 'Select Attack Target'
    }
    overlay.value = 'select_target'
    overlayTitle.value = 'Attack'
}

// When clicking opposing creature (just for info, cannot attack)
const handleClickOpposingCreature = (creature_id: string) => {
    console.log('handleClickOpposingCreature', creature_id)
    selectedEntity.value = { type: 'creature', id: creature_id, isOwned: false }
    overlay.value = 'entity_detail'
    overlayTitle.value = 'Enemy Creature'
}

// When clicking own hero
const handleClickOwnHero = () => {
    if (!ownHero.value || !viewer.value) return
    console.log('handleClickOwnHero', ownHero.value.hero_id)
    // Store the side (viewer) as the ID since heroes are keyed by side in the state
    selectedEntity.value = { type: 'hero', id: viewer.value, isOwned: true }
    overlay.value = 'entity_detail'
    overlayTitle.value = 'Hero Power'
}

// When clicking opposing hero (just for info, cannot use)
const handleClickOpposingHero = () => {
    if (!opposingHero.value || !viewer.value) return
    console.log('handleClickOpposingHero', opposingHero.value.hero_id)
    // Store the opposing side as the ID
    const opposingSide = viewer.value === 'side_a' ? 'side_b' : 'side_a'
    selectedEntity.value = { type: 'hero', id: opposingSide, isOwned: false }
    overlay.value = 'entity_detail'
    overlayTitle.value = 'Enemy Hero'
}

/* Action Handlers - From EntityDetail Component */

// Place creature card on board
const handlePlaceCreature = (card_id: string) => {
    console.log('handlePlaceCreature', card_id)
    selectedCardId.value = card_id
    overlay.value = 'place_creature'
    overlayTitle.value = 'Place Creature'
}

// Cast spell card
const handleCastSpell = (card_id: string) => {
    console.log('handleCastSpell', card_id)
    const card = get_card(card_id)
    if (!card) return

    // If spell requires target, open target selector
    if (requiresTarget(card)) {
        pendingPlay.value = { card_id, position: 0 }
        targetingState.value = {
            sourceType: 'spell',
            sourceId: card_id,
            allowedTypes: convertAllowedTargets(getAllowedTargets(card)),
            scope: getSpellTargetScope(card),
            sourceCard: card,
            errorMessage: null,
            title: 'Cast Spell'
        }
        overlay.value = 'select_target'
        overlayTitle.value = 'Select Target'
        return
    }

    // No target required, cast immediately
    gameStore.playCard(card_id, 0)
    closeOverlay()
}

// Creature attack
const handleAttack = (creature_id: string) => {
    console.log('handleAttack', creature_id)
    const creature = get_creature(creature_id)
    if (!creature) return

    targetingState.value = {
        sourceType: 'creature',
        sourceId: creature_id,
        allowedTypes: 'both',  // Creatures can attack both heroes and other creatures
        scope: 'enemy',
        sourceCard: creature,
        errorMessage: creature.exhausted ? 'Creature is exhausted' : null,
        title: 'Select Attack Target'
    }
    overlay.value = 'select_target'
    overlayTitle.value = 'Attack'
}

// Use hero power
const handleUseHero = (side_id: string) => {
    console.log('handleUseHero', side_id)
    const hero = getHero(side_id)
    if (!hero) return

    targetingState.value = {
        sourceType: 'hero',
        sourceId: hero.hero_id,  // Use the actual hero_id for the backend command
        allowedTypes: 'both',  // Hero powers can target various things
        scope: 'enemy', // Most hero powers target enemies
        sourceCard: null,
        errorMessage: !canUseHero.value ? 'Cannot use hero power' : null,
        title: 'Use Hero Power'
    }
    overlay.value = 'select_target'
    overlayTitle.value = 'Hero Power'
}

/* Placement and Targeting Callbacks */

// When placement position is selected from PlaceCreature
const onPlacementSelected = (payload: { card_id: string; position: number; allowedTargets: Array<'card' | 'hero' | 'any'>; targetScope: 'enemy' | 'friendly' }) => {
    console.log('onPlacementSelected', payload)

    // If battlecry requires target, open target selector
    pendingPlay.value = { card_id: payload.card_id, position: payload.position }

    const card = get_card(payload.card_id)
    targetingState.value = {
        sourceType: 'battlecry',
        sourceId: payload.card_id,
        allowedTypes: convertAllowedTargets(payload.allowedTargets),
        scope: payload.targetScope,
        sourceCard: card || null,
        errorMessage: null,
        title: 'Choose Battlecry Target'
    }
    overlay.value = 'select_target'
    overlayTitle.value = 'Battlecry Target'
}

// When target is selected from Target component
const onTargetSelected = (target: { target_type: 'creature' | 'hero'; target_id: string }) => {
    console.log('onTargetSelected', target)
    if (!targetingState.value) return

    const { sourceType, sourceId } = targetingState.value

    // Handle battlecry targeting (card being played with battlecry)
    if (sourceType === 'battlecry' && pendingPlay.value) {
        const { card_id, position } = pendingPlay.value
        // Convert 'creature' to 'card' for backend compatibility
        const backendTarget = {
            target_type: target.target_type === 'creature' ? 'card' as const : target.target_type,
            target_id: target.target_id
        }
        gameStore.playCard(card_id, position, backendTarget)
        pendingPlay.value = null
        closeOverlay()
        return
    }

    // Handle spell targeting
    if (sourceType === 'spell' && pendingPlay.value) {
        const { card_id } = pendingPlay.value
        const backendTarget = {
            target_type: target.target_type === 'creature' ? 'card' as const : target.target_type,
            target_id: target.target_id
        }
        gameStore.playCard(card_id, 0, backendTarget)
        pendingPlay.value = null
        closeOverlay()
        return
    }

    // Handle creature attack
    if (sourceType === 'creature') {
        if (target.target_type === 'creature') {
            gameStore.useCardOnCard(sourceId, target.target_id)
        } else {
            gameStore.useCardOnHero(sourceId, target.target_id)
        }
        closeOverlay()
        return
    }

    // Handle hero power
    if (sourceType === 'hero') {
        if (target.target_type === 'creature') {
            gameStore.useHeroOnCard(sourceId, target.target_id)
        } else {
            gameStore.useHeroOnHero(sourceId, target.target_id)
        }
        closeOverlay()
        return
    }
}

/* Menu Handlers */

const handleEndTurn = () => {
    if (gameOver.value.isGameOver) return
    gameStore.endTurn()
}

const handleMenuClick = () => {
    overlay.value = 'menu'
    overlayTitle.value = "Menu"
}

const handleClickUpdates = () => {
    overlay.value = 'updates'
    overlayTitle.value = "Game Updates"
}

const handleClickDebug = () => {
    overlay.value = 'debug'
    overlayTitle.value = "Debug"
}

/* Utility Functions */

// Close overlay and clear state
const closeOverlay = () => {
    overlay.value = null
    overlayTitle.value = ''
    targetingState.value = null
    selectedEntity.value = null
    selectedCardId.value = null
    pendingPlay.value = null
}

// Clear local UI state when game over is detected
const clearLocalState = () => {
    closeOverlay()
}

function requiresTarget(card: CardInPlay): boolean {
    const traits = card.traits || []

    // Check for spell with targeting
    if (card.card_type === 'spell') {
        for (const trait of traits) {
            const actions = trait.actions || []
            for (const action of actions) {
                // Actions that require targeting (single and cleave need targets, AOE doesn't)
                if ((action.action === 'damage' || action.action === 'heal') &&
                    action.scope !== 'all') {
                    return true
                }
            }
        }
    }

    return false
}

function getAllowedTargets(card: CardInPlay): Array<'card' | 'hero' | 'any'> {
    const allowed = new Set<'card' | 'hero' | 'any'>()
    const traits = card.traits || []

    for (const trait of traits) {
        const actions = trait.actions || []
        for (const action of actions) {
            if (action.action === 'damage') {
                if (action.target === 'creature' || action.target === 'enemy') {
                    allowed.add('card')
                }
                if (action.target === 'hero' || action.target === 'enemy') {
                    allowed.add('hero')
                }
            }
            if (action.action === 'heal') {
                // Heal targets friendlies (same side)
                // For now, map this to the same targeting system
                if (action.target === 'creature' || action.target === 'friendly') {
                    allowed.add('card')
                }
                if (action.target === 'hero' || action.target === 'friendly') {
                    allowed.add('hero')
                }
            }
        }
    }

    if (allowed.size === 0) allowed.add('any')
    return Array.from(allowed)
}

function getSpellTargetScope(card: CardInPlay): 'enemy' | 'friendly' {
    const traits = card.traits || []

    for (const trait of traits) {
        const actions = trait.actions || []
        for (const action of actions) {
            // Heal actions target friendly units
            if (action.action === 'heal') {
                return 'friendly'
            }
            // Damage actions target enemies
            if (action.action === 'damage') {
                return 'enemy'
            }
        }
    }

    return 'enemy'
}

// Convert old target format to new format
function convertAllowedTargets(targets: Array<'card' | 'hero' | 'any'>): 'creature' | 'hero' | 'both' {
    if (targets.includes('any')) return 'both'
    if (targets.includes('card') && targets.includes('hero')) return 'both'
    if (targets.includes('card')) return 'creature'
    if (targets.includes('hero')) return 'hero'
    return 'both'
}

/* Lifecycle and Watchers */

watch(title, async (newTitle) => {
    if (newTitle) {
        await gameStore.connectToGame(route.params.game_id as string)
    }
}, { immediate: true })

// Clear local state when game over is detected
watch(() => gameOver.value.isGameOver, (isGameOver) => {
    if (isGameOver) {
        clearLocalState()
        showingGameOver.value = true
    }
})

// Handle escape key to close overlay
const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && overlay.value) {
        closeOverlay()
    }
}

onMounted(() => {
    window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown)
    gameStore.disconnect()
})
</script>

<style scoped>
.board {
    height: 100vh;
}
</style>

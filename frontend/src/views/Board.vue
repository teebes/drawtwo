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
                    <div class="w-24 flex flex-col items-center justify-center border-r border-gray-700" :class="{ 'bg-yellow-500/20': gameState.active === topSide }">
                        <div class="">{{ opposingHeroInitials }}</div>
                        <div class="">{{ opposingHero?.health }}</div>
                    </div>

                    <!-- Recent Updates -->
                    <div class="flex flex-1 flex-col p-2 justify-center items-center cursor-pointer" @click="handleClickUpdates">
                        <Update v-if="displayUpdates.length > 0" :update="displayUpdates[displayUpdates.length - 1]" />
                    </div>

                    <!-- Menu -->
                    <div class="w-24 flex justify-center items-center text-center border-l border-gray-700">
                        <span class="inline-block" @click="handleMenuClick">
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
                        <div v-for="card in opposingBoard" :key="card.card_id" class="p-1">
                            <GameCard v-if="card"
                                      class="flex-grow-0"
                                      :card="card"
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
                        <div v-for="card in ownBoard" :key="card.card_id" class="p-1">
                            <GameCard v-if="card"
                                      class="flex-grow-0 cursor-pointer"
                                      :card="card"
                                      @click="handleUseCard(card.card_id)"
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
                    <div class="hero w-24 h-full border-r border-gray-700 flex flex-col items-center justify-center cursor-pointer"
                         :class="{
                           'bg-yellow-500/20': gameState.active === bottomSide,
                           'opacity-50': !canUseHero
                         }"
                         @click="handleUseHero()">
                        <div class="hero-name">{{ ownHeroInitials }}</div>
                        <div class="hero-health">{{ ownHero?.health }}</div>
                    </div>

                    <!-- Hand -->
                    <div class="hand overflow-x-auto flex flex-row">
                        <div v-for="card_id in ownHand" :key="card_id" class="p-1">
                            <GameCard v-if="get_card(card_id)"
                                      class="flex-grow-0 cursor-pointer"
                                      :card="get_card(card_id)!"
                                      :active="isHandCardActive(card_id)"
                                      @click="handleSelectHandCard(card_id)"
                                      compact />
                        </div>
                    </div>
                </div>
            </div>

        </main>

        <!-- Overlay Mode -->
         <main v-else class="board flex-1 flex flex-col max-w-md w-full border-r border-l border-gray-700">
            <!-- Header -->
            <OverlayHeader :text="overlay_text" @close="overlay = null" />

            <!-- Hand Card Board Selection Overlay-->
            <PlayCard
                v-if="overlay == 'select_hand_card'"
                :game-state="gameState"
                :selected-hand-card="selected_hand_card"
                :own-board="ownBoard"
                :own-energy="ownEnergy"
                @target-required="onPlayTargetRequired"
                @close-overlay="closeOverlay"
            />

            <!-- Target Selection Overlays -->
            <Target
                v-if="overlay == 'target_spell' || overlay == 'target_battlecry' || overlay == 'target_attack' || overlay == 'target_hero'"
                :opposing-board="opposingBoard"
                :opposing-hero="opposingHero"
                :allowed-target-types="targetingConfig.allowedTypes"
                :source-card="targetingConfig.sourceCard"
                :error-message="targetingConfig.errorMessage"
                :title="targetingConfig.title"
                @target-selected="onTargetSelected"
                @cancelled="closeOverlay"
            />

            <!-- Menu Overlay -->
            <div v-if="overlay == 'menu'">
                <div class="flex flex-col items-center justify-center space-y-8 my-8">
                    <div class="text-2xl cursor-pointer" @click="handleClickUpdates">
                        Updates
                    </div>

                    <div v-if="canEditTitle" class="text-2xl cursor-pointer" @click="handleClickDebug">
                        Debug
                    </div>

                    <div class="text-2xl">
                        <router-link :to="{ name: 'Title', params: { slug: titleStore.titleSlug } }">
                            Exit Game
                        </router-link>
                    </div>
                </div>
            </div>

            <!-- Updates Overlay -->
            <div v-if="overlay == 'updates'" class="flex-1 min-h-0">
                <div class="flex flex-col h-full border-gray-700 overflow-y-auto">
                    <div class="flex border-gray-700 items-center justify-center py-2" :class="{ 'border-b': update.type === 'update_end_turn' }"
                         v-for="update in displayUpdates" :key="update.timestamp">
                        <Update :update="update" />
                    </div>
                </div>
            </div>

            <!-- Debug Overlay -->
            <DebugOverlay v-if="overlay == 'debug'" :game-id="gameId" />

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
import type { CardInPlay } from '../types/game'
import { useAuthStore } from '../stores/auth'
import { useTitleStore } from '../stores/title'
import { useGameStore } from '../stores/game'
import { storeToRefs } from 'pinia'

import GameCard from '../components/game/GameCard.vue'
import GameButton from '../components/ui/GameButton.vue'
// Board Components
import PlayCard from '../components/game/board/PlayCard.vue'
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
  ownHeroInitials,
  ownHandSize,
  ownDeckSize,
  ownHand,
  ownEnergy,
  ownEnergyPool,
  ownBoard,
  opposingHero,
  opposingHeroInitials,
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

// Local UI state only
const selected_hand_card = ref<string | null>(null)
const overlay = ref<'select_hand_card' | 'target_spell' | 'target_battlecry' | 'target_attack' | 'target_hero' | 'menu' | 'updates' | 'debug' | null>(null)
const overlay_text = ref<string | null>(null)

// Targeting state
interface TargetingState {
    sourceType: 'creature' | 'hero' | 'spell'
    sourceId: string
    allowedTypes: 'creature' | 'hero' | 'both'
}
const targetingState = ref<TargetingState | null>(null)

// Pending play context when a target is required (battlecry/spell)
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

const isHandCardActive = (card_id: string | number) => {
    return gameStore.isHandCardActive(String(card_id))
}

// Computed targeting configuration
const targetingConfig = computed(() => {
    if (!targetingState.value) {
        return {
            allowedTypes: 'both' as const,
            sourceCard: null,
            errorMessage: null,
            title: 'Select Target'
        }
    }

    const { sourceType, sourceId, allowedTypes } = targetingState.value
    let sourceCard: CardInPlay | null = null
    let errorMessage: string | null = null
    let title = 'Select Target'

    // Get source card if applicable
    if (sourceType === 'creature' || sourceType === 'spell') {
        sourceCard = get_card(sourceId) || null
    }

    // Validate based on source type
    if (sourceType === 'creature' && sourceCard) {
        if (sourceCard.exhausted) {
            errorMessage = 'Creature is exhausted'
        }
        title = 'Attack Target'
    } else if (sourceType === 'hero') {
        if (!canUseHero.value) {
            errorMessage = 'Hero cannot be used'
        }
        title = 'Use Hero Power'
    } else if (sourceType === 'spell' && sourceCard) {
        const availableEnergy = ownEnergy.value
        if (sourceCard.cost > availableEnergy) {
            errorMessage = 'Not enough energy'
        }
        title = 'Cast Spell'
    }

    return {
        allowedTypes,
        sourceCard,
        errorMessage,
        title
    }
})

/* Handlers */

const handleEndTurn = () => {
    if (gameOver.value.isGameOver) return
    gameStore.endTurn()
}

const handleSelectHandCard = (card_id: string) => {
    console.log('handleSelectHandCard', card_id)
    const card = get_card(card_id)
    if (!card) return

    // Spells require target selection
    if (card.card_type === 'spell') {
        selected_hand_card.value = card_id
        if (requiresTargetOnPlay(card)) {
            console.log('requiresTargetOnPlay', card)
            // Open target selection for spells
            // After target is selected, onTargetSelected() handles the execution
            // via gameStore.playCard()
            pendingPlay.value = { card_id, position: 0 }
            targetingState.value = {
                sourceType: 'spell',
                sourceId: card_id,
                allowedTypes: convertAllowedTargets(getAllowedTargets(card))
            }
            overlay.value = 'target_spell'
            overlay_text.value = 'Cast Spell'
            return
        }
        // If no target required, just play immediately
        gameStore.playCard(card_id, 0)
        return
    }

    // Default: show placement overlay for creatures
    overlay.value = 'select_hand_card'
    overlay_text.value = 'Play Card'
    selected_hand_card.value = card_id
}

// Creature attack handler
const handleUseCard = (card_id: string | number) => {
    const card = get_card(card_id)
    if (!card) return

    targetingState.value = {
        sourceType: 'creature',
        sourceId: String(card_id),
        allowedTypes: 'both'  // Creatures can attack both heroes and other creatures
    }
    overlay.value = 'target_attack'
    overlay_text.value = 'Attack'
}

// Hero power handler
const handleUseHero = () => {
    if (!ownHero.value) return

    targetingState.value = {
        sourceType: 'hero',
        sourceId: ownHero.value.hero_id,
        allowedTypes: 'both'  // Heroes can target both creatures and heroes
    }
    overlay.value = 'target_hero'
    overlay_text.value = 'Use Hero Power'
}

const handleMenuClick = () => {
    overlay.value = 'menu'
    overlay_text.value = "Menu"
}

const handleClickUpdates = () => {
    overlay.value = 'updates'
    overlay_text.value = "Updates"
}

const handleClickDebug = () => {
    overlay.value = 'debug'
    overlay_text.value = "Debug"
}

// When PlayCard determines a target is required (battlecry after placement)
// After target is selected, onTargetSelected() handles the execution via gameStore.playCard()
const onPlayTargetRequired = (payload: { card_id: string; position: number; allowedTargets: Array<'card' | 'hero' | 'any'> }) => {
    pendingPlay.value = { card_id: payload.card_id, position: payload.position }
    targetingState.value = {
        sourceType: 'creature',
        sourceId: payload.card_id,
        allowedTypes: convertAllowedTargets(payload.allowedTargets)
    }
    overlay.value = 'target_battlecry'
    overlay_text.value = 'Choose Battlecry Target'
}

// Receive target from Target component and execute appropriate command
const onTargetSelected = (target: { target_type: 'creature' | 'hero'; target_id: string }) => {
    if (!targetingState.value) return

    const { sourceType, sourceId } = targetingState.value

    // Handle battlecry targeting (card being played)
    if (pendingPlay.value) {
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

    // Note: Spell targeting is handled by the pendingPlay check above
    // since spells always set pendingPlay before opening the target overlay
}

// Close overlay and clear state
const closeOverlay = () => {
    overlay.value = null
    overlay_text.value = null
    targetingState.value = null
    selected_hand_card.value = null
    pendingPlay.value = null
}

// Clear local UI state when game over is detected
const clearLocalState = () => {
    closeOverlay()
}

// Hero clicking now handled directly by UseCard component


// All computed properties are now handled by the game store


// All WebSocket and game state management moved to store

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

function requiresTargetOnPlay(card: any): boolean {
    const traits = card.traits || []
    const battlecry = traits.find((t: any) => t.type === 'battlecry')
    if (!battlecry) return false
    return hasTargetingActions([battlecry])
}

function hasTargetingActions(traits: any[]): boolean {
    for (const trait of traits) {
        const actions = trait.actions || []
        for (const action of actions) {
            if (action.action === 'damage') {
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

// Convert old target format to new format
function convertAllowedTargets(targets: Array<'card' | 'hero' | 'any'>): 'creature' | 'hero' | 'both' {
    if (targets.includes('any')) return 'both'
    if (targets.includes('card') && targets.includes('hero')) return 'both'
    if (targets.includes('card')) return 'creature'
    if (targets.includes('hero')) return 'hero'
    return 'both'
}
</script>

<style scoped>
.board {
    height: 100vh;
}
</style>
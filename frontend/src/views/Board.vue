<template>
    <div class="min-h-screen flex flex-row justify-center relative" v-if="!loading">

        <!-- Game Over Overlay -->
        <GameOverOverlay v-if="showingGameOver" :game-over="gameOver" :viewer="viewer" />

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
                    v-if="!gameOver.isGameOver"
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
                    <div class="hero w-24 h-full border-r border-gray-700 flex flex-col items-center justify-center" :class="{ 'bg-yellow-500/20': gameState.active === bottomSide }">
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
            <div class="flex flex-row w-full h-24 border-b border-gray-700 items-center">
                <!-- Display Text -->
                <div class="flex-1 text-center text-gray-400">{{ overlay_text }}</div>

                <!-- Close Button-->
                <div
                  class="w-24 h-full flex items-center justify-center cursor-pointer group relative border-l border-gray-700"
                  @click="overlay = null"
                  title="Click to close overlay"
                >
                  <span
                    class="text-6xl text-gray-500 group-hover:text-gray-100 select-none pointer-events-none"
                    style="line-height: 1;"
                  >&times;</span>
                  <span class="sr-only">Close overlay</span>
                </div>
            </div>

            <!-- Hand Card Board Selection Overlay-->
            <PlayCard
                v-if="overlay == 'select_hand_card'"
                :game-state="gameState"
                :selected-hand-card="selected_hand_card"
                :own-board="ownBoard"
                :own-energy="ownEnergy"
                @target-required="onPlayTargetRequired"
                @close-overlay="() => {
                    overlay = null
                    selected_hand_card = null
                    overlay_text = null
                }"
            />

            <UseCard
                v-if="overlay == 'use_card'"
                :game-state="gameState"
                :card="selected_use_card"
                :own-board="ownBoard"
                :opposing-board="opposingBoard"
                :opposing-hero="opposingHero"
                :opposing-hero-initials="opposingHeroInitials"
                :mode="useCardMode"
                :allowed-target-types="allowedTargetTypes"
                @target-selected="onTargetSelected"
                @close-overlay="() => {
                    overlay = null
                    selected_use_card = null
                    overlay_text = null
                }"

            />

            <!-- Menu Overlay -->
            <div v-if="overlay == 'menu'">
                <div class="flex flex-col items-center justify-center space-y-8 my-8">
                    <div class="text-2xl cursor-pointer" @click="handleClickUpdates">
                        Updates
                    </div>

                    <div class="text-2xl">
                        <router-link :to="{ name: 'Title', params: { slug: titleStore.titleSlug } }">
                            Exit Game
                        </router-link>
                    </div>
                </div>
            </div>

            <!-- Updates Overlay -->
            <div v-if="overlay == 'updates'">
                <div class="flex flex-col border-gray-700 overflow-y-scroll">
                    <div class="flex flex-grow border-gray-700 items-center justify-center py-2" :class="{ 'border-b': update.type === 'update_end_turn' }"
                         v-for="update in displayUpdates" :key="update.timestamp">
                        <Update :update="update" />
                    </div>
                </div>
            </div>

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
import { useTitleStore } from '../stores/title'
import { useGameStore } from '../stores/game'
import { storeToRefs } from 'pinia'

import GameCard from '../components/game/GameCard.vue'
import GameButton from '../components/ui/GameButton.vue'
// Board Components
import PlayCard from '../components/game/board/PlayCard.vue'
import UseCard from '../components/game/board/UseCard.vue'
import GameOverOverlay from '../components/game/board/GameOverOverlay.vue'
import Update from '../components/game/board/Update.vue'

const route = useRoute()
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
  displayUpdates
} = storeToRefs(gameStore)

// Local UI state only
const selected_hand_card = ref<string | null>(null)
const selected_use_card = ref<CardInPlay | null>(null)
const overlay = ref<'select_hand_card' | 'use_card' | 'menu' | 'updates' | null>(null)
const overlay_text = ref<string | null>(null)
const useCardMode = ref<'use' | 'select'>('use')
const allowedTargetTypes = ref<Array<'card' | 'hero' | 'any'>>(['any'])

// Pending play context when a target is required (battlecry/spell)
const pendingPlay = ref<{ card_id: string; position: number } | null>(null)

const showingGameOver = ref(false)

const title = computed(() => titleStore.currentTitle)

// Helper methods from store
const get_card = (card_id: string | number) => {
    return gameStore.getCard(String(card_id))
}

const isHandCardActive = (card_id: string | number) => {
    return gameStore.isHandCardActive(String(card_id))
}

/* Handlers */

const handleEndTurn = () => {
    if (gameOver.value.isGameOver) return
    gameStore.endTurn()
}

const handleSelectHandCard = (card_id: string) => {
    if (gameOver.value.isGameOver) return
    const card = get_card(card_id)
    if (!card) return

    // Spells or minions with battlecry targeting may require target first/after placement
    if (card.card_type === 'spell') {
        selected_hand_card.value = card_id
        if (requiresTargetOnPlay(card)) {
            // Open target selection directly for spells
            pendingPlay.value = { card_id, position: 0 }
            allowedTargetTypes.value = getAllowedTargets(card)
            selected_use_card.value = card
            useCardMode.value = 'select'
            overlay.value = 'use_card'
            overlay_text.value = 'Use Card'
            return
        }
        // If no target required, just play immediately
        gameStore.playCard(card_id, 0)
        return
    }

    // Default: show placement overlay for minions
    overlay.value = 'select_hand_card'
    overlay_text.value = 'Play Card'
    selected_hand_card.value = card_id
}

// Card placement now handled directly by PlayCard component

const handleUseCard = (card_id: string | number) => {
    if (gameOver.value.isGameOver) return

    overlay.value = 'use_card'
    overlay_text.value = "Use Card"
    selected_use_card.value = get_card(card_id) || null
    useCardMode.value = 'use'
}

const handleMenuClick = () => {
    overlay.value = 'menu'
    overlay_text.value = "Menu"
}

const handleClickUpdates = () => {
    overlay.value = 'updates'
    overlay_text.value = "Updates"
}

// When PlayCard determines a target is required
const onPlayTargetRequired = (payload: { card_id: string; position: number; allowedTargets: Array<'card' | 'hero' | 'any'> }) => {
    pendingPlay.value = { card_id: payload.card_id, position: payload.position }
    allowedTargetTypes.value = payload.allowedTargets
    selected_use_card.value = get_card(payload.card_id) || null
    useCardMode.value = 'select'
    overlay.value = 'use_card'
    overlay_text.value = 'Use Card'
}

// Receive target from UseCard in selection mode and submit play with target
const onTargetSelected = (target: { target_type: 'card' | 'hero'; target_id: string }) => {
    if (!pendingPlay.value) return
    const { card_id, position } = pendingPlay.value
    gameStore.playCard(card_id, position, target)
    pendingPlay.value = null
}

// Clear local UI state when game over is detected
const clearLocalState = () => {
    selected_hand_card.value = null
    selected_use_card.value = null
    overlay.value = null
    overlay_text.value = null
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
        overlay.value = null
        selected_hand_card.value = null
        selected_use_card.value = null
        overlay_text.value = null
        pendingPlay.value = null
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
            if (action.target === 'minion' || action.target === 'enemy') {
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
</script>

<style scoped>
.board {
    height: 100vh;
}
</style>
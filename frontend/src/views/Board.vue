<template>
    <div class="min-h-screen flex flex-row justify-center relative" v-if="!loading">

        <!-- Game Over Overlay -->
        <GameOverOverlay :game-over="gameOver" :viewer="viewer" />

        <!-- Normal Mode -->
        <main v-if="!overlay" class="board flex-1 flex flex-col max-w-md w-full border-r border-l border-gray-700">

            <!-- Opponent Side -->
            <div class="side-b flex-1 flex flex-col">

                <!-- Header -->
                 <div class="h-24 flex flex-row justify-between border-b border-gray-700">
                    <!-- Enemy Hero-->
                    <div class="w-24 flex flex-col items-center justify-center border-r border-gray-700" :class="{ 'bg-yellow-500/20': gameState?.active === topSide }">
                        <div class="">{{ opposingHeroInitials }}</div>
                        <div class="">{{ opposingHero?.health }}</div>
                    </div>

                    <div class="flex flex-1 flex-row items-center justify-center space-x-4">
                        <div>{{ gameState?.phase }}</div>
                        <!-- <div>{{ gameState?.active }}</div> -->
                    </div>

                    <!-- Menu -->
                    <div class="w-24 flex justify-center items-center text-center border-l border-gray-700">
                        <span class="inline-block">
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
                        <div>{{ opposingEnergy }}</div>
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
            <div class="flex flex-row-reverse border-gray-700 border-t border-b">
                <GameButton
                    variant="secondary"
                    class="m-2"
                    @click="handleEndTurn">End Turn</GameButton>
            </div>

            <!-- Viewer Side-->
            <div class="side-a flex-1 flex flex-col">
                <!-- Viewer Board-->
                <div class="viewer-board flex-1 flex flex-row bg-gray-800 items-center overflow-x-auto">
                    <div class="lane flex flex-row h-24 mx-auto">
                        <div v-for="card in ownBoard" :key="card.card_id" class="p-1">
                            <GameCard v-if="card"
                                      class="flex-grow-0"
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
                        <div>{{ ownEnergy }}</div>
                    </div>
                 </div>

                <!-- Footer -->
                <div class="h-24 flex flex-row border-t border-gray-700">
                    <!-- Viewer Hero -->
                    <div class="hero w-24 h-full border-r border-gray-700 flex flex-col items-center justify-center" :class="{ 'bg-yellow-500/20': gameState?.active === bottomSide }">
                        <div class="hero-name">{{ ownHeroInitials }}</div>
                        <div class="hero-health">{{ ownHero?.health }}</div>
                    </div>

                    <!-- Hand -->
                    <div class="hand overflow-x-auto flex flex-row">
                        <div v-for="card_id in ownHand" :key="card_id" class="p-1">
                            <GameCard v-if="get_card(card_id)"
                                      class="flex-grow-0"
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
                @close-overlay="() => {
                    overlay = null
                    selected_use_card = null
                    overlay_text = null
                }"

            />

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
import { watch, computed, ref, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import type { CardInPlay } from '../types/game'
import { useTitleStore } from '../stores/title.js'
import { useGameStore } from '../stores/game'
import { storeToRefs } from 'pinia'

import GameCard from '../components/game/GameCard.vue'
import GameButton from '../components/ui/GameButton.vue'
// Board Components
import PlayCard from '../components/game/board/PlayCard.vue'
import UseCard from '../components/game/board/UseCard.vue'
import GameOverOverlay from '../components/game/board/GameOverOverlay.vue'

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
  ownBoard,
  opposingHero,
  opposingHeroInitials,
  opposingHandSize,
  opposingDeckSize,
  opposingEnergy,
  opposingBoard,
  topSide,
  bottomSide
} = storeToRefs(gameStore)

// Local UI state only
const selected_hand_card = ref<string | null>(null)
const selected_use_card = ref<CardInPlay | null>(null)
const overlay = ref<'select_hand_card' | 'use_card' | null>(null)
const overlay_text = ref<string | null>(null)


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
    overlay.value = 'select_hand_card'
    overlay_text.value = "Play Card"
    selected_hand_card.value = card_id
}

// Card placement now handled directly by PlayCard component

const handleUseCard = (card_id: string | number) => {
    if (gameOver.value.isGameOver) return

    overlay.value = 'use_card'
    overlay_text.value = "Use Card"
    selected_use_card.value = get_card(card_id) || null
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
    }
})

onUnmounted(() => {
    gameStore.disconnect()
})
</script>

<style scoped>
.board {
    height: 100vh;
}
</style>
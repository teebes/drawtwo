<template>
    <div class="min-h-screen flex flex-row justify-center">

        <main class="board flex-1 flex flex-col max-w-md w-full border-r border-l border-gray-700">

            <!-- Side B -->
            <div class="side-b flex-1 flex flex-col">

                <!-- Header -->
                 <div class="h-24 flex flex-row justify-between border-b border-gray-700">
                    <!-- Enemy Hero-->
                    <div class="w-24 flex flex-col items-center justify-center border-r border-gray-700">
                        <div class="">{{ opposing_hero_initials }}</div>
                        <div class="">{{ opposing_hero?.health }}</div>
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
                        <div>{{ opposing_deck_size }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div>Hand</div>
                        <div>{{ opposing_hand_size }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div>Energy</div>
                        <div>{{ opposing_energy }}</div>
                    </div>
                 </div>

                 <!-- Upper Board -->
                 <div class="upper-board flex-1 flex flex-row bg-gray-800 items-center">
                    <div class="lane flex flex-row w-full h-24 justify-center overflow-x-auto">
                        <div v-for="card_id in opposing_board" :key="card_id" class="p-1">
                            <GameCard v-if="get_card(card_id)"
                                      class="flex-grow-0"
                                      :card="get_card(card_id)!"
                                      compact />
                        </div>
                    </div>
                 </div>
            </div>

            <!-- Mid Section -->
            <div class="flex flex-row-reverse border-gray-700 border-t border-b">
                <GameButton variant="secondary" class="m-2">End Turn</GameButton>
            </div>

            <!-- Side A-->
            <div class="side-a flex-1 flex flex-col">
                <div class="upper-board flex-1 flex flex-row bg-gray-800 items-center">
                    <div class="lane flex flex-row w-full h-24 justify-center overflow-x-auto">
                        <div v-for="card_id in own_board" :key="card_id" class="p-1">
                            <GameCard v-if="get_card(card_id)"
                                      class="flex-grow-0"
                                      :card="get_card(card_id)!"
                                      compact />
                        </div>
                    </div>
                 </div>

                <!-- Stats -->
                 <div class="flex flex-row justify-around border-t border-gray-700 p-2">
                    <div class="flex flex-col text-center">
                        <div>Deck</div>
                        <div>{{ own_deck_size }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div>Hand</div>
                        <div>{{ own_hand_size }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div>Energy</div>
                        <div>{{ own_energy }}</div>
                    </div>
                 </div>

                <!-- Footer -->
                <div class="h-24 flex flex-row border-t border-gray-700">
                    <!-- Viewer Hero -->
                    <div class="hero w-24 h-full border-r border-gray-700 flex flex-col items-center justify-center">
                        <div class="hero-name">{{ own_hero_initials }}</div>
                        <div class="hero-health">{{ own_hero?.health }}</div>
                    </div>

                    <!-- Hand -->
                    <div class="hand overflow-x-auto flex flex-row">
                        <div v-for="card_id in own_hand" :key="card_id" class="p-1">
                            <GameCard v-if="get_card(card_id)"
                                      class="flex-grow-0"
                                      :card="get_card(card_id)!"
                                      compact />
                        </div>
                    </div>
                </div>
            </div>


        </main>
    </div>
</template>

<script setup lang="ts">
import { watch, computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { CardInPlay } from '../types/game'
import type { GameState } from '../types/game'
import { useTitleStore } from '../stores/title.js'
import axios from '../config/api.js'
import GameCard from '../components/game/GameCard.vue'
import { makeInitials } from '../utils'
import GameButton from '../components/ui/GameButton.vue'

const route = useRoute()
const router = useRouter()
const titleStore = useTitleStore()

const loading = ref(true)
const gameState = ref<GameState | null>(null)
const viewer = ref<'side_a' | 'side_b' | null>(null)
const isVsAi = ref(false)
const error = ref<string | null>(null)
const cardNameMap = ref<Record<string, string>>({})

const title = computed(() => titleStore.currentTitle)

/*
    Own Data

    We want whoever is viewing their game to be at the bottom. Determine whether
    the viewer is side_a or side_b.
*/
const own_hero = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.heroes.side_a
    } else {
        return gameState.value?.heroes.side_b
    }
})
const own_hero_initials = computed(() => {
    if (own_hero.value) {
        return makeInitials(own_hero.value.name)
    }
    return ''
})
const own_hand_size = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.hands.side_a.length
    } else {
        return gameState.value?.hands.side_b.length
    }
})
const own_deck_size = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.decks.side_a.length
    } else {
        return gameState.value?.decks.side_b.length
    }
})
const own_hand = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.hands.side_a
    } else {
        return gameState.value?.hands.side_b
    }
})
const own_energy = computed(() => {
    if (!gameState.value || !gameState.value.mana_pool || !gameState.value.mana_used || !viewer.value) {
        return 0
    }
    if (viewer.value === 'side_a') {
        const pool = gameState.value.mana_pool.side_a
        const used = gameState.value.mana_used.side_a
        if (pool === undefined || used === undefined) return 0
        return pool - used
    } else {
        const pool = gameState.value.mana_pool.side_b
        const used = gameState.value.mana_used.side_b
        if (pool === undefined || used === undefined) return 0
        return pool - used
    }
})
const own_board = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.board.side_a
    } else {
        return gameState.value?.board.side_b
    }
})

/*
    Opponent Data

    We want whoever is viewing their game to be at the bottom. Because of this,
    we have to use computed data to determine which side is on top and fetch the
    appropriate data.
*/
const opposing_hero = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.heroes.side_b
    } else {
        return gameState.value?.heroes.side_a
    }
})
const opposing_hero_initials = computed(() => {
    if (opposing_hero.value) {
        return makeInitials(opposing_hero.value.name)
    }
    return ''
})
const opposing_hand_size = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.hands.side_b.length
    } else {
        return gameState.value?.hands.side_a.length
    }
})
const opposing_deck_size = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.decks.side_b.length
    } else {
        return gameState.value?.decks.side_a.length
    }
})
const opposing_energy = computed(() => {
    if (viewer.value === 'side_a') {
        const pool = gameState.value?.mana_pool.side_b
        const used = gameState.value?.mana_used.side_b
        if (pool === undefined || used === undefined) return 0
        return pool - used
    } else {
        const pool = gameState.value?.mana_pool.side_a
        const used = gameState.value?.mana_used.side_a
        if (pool === undefined || used === undefined) return 0
        return pool - used
    }
})
const opposing_board = computed(() => {
    if (viewer.value === 'side_a') {
        return gameState.value?.board.side_b
    } else {
        return gameState.value?.board.side_a
    }
})

const get_card = (card_id: string) => {
    return gameState.value?.cards[card_id]
}

const fetchGameState = async () => {
  try {
    const gameId = route.params.game_id
    const response = await axios.get(`/gameplay/games/${gameId}/`)

    console.log(response.data)

    const data = response.data
    viewer.value = data.viewer
    gameState.value = data;
    isVsAi.value = data.is_vs_ai;

    // Build card name mapping from the game state
    // In practice, you'd fetch card templates separately
    Object.values(data.cards).forEach((card: any) => {
      cardNameMap.value[card.template_slug] = card.template_slug.replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase())
    })

  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error occurred'
  } finally {
    loading.value = false
  }
}

watch(title, async (newTitle) => {
    if (newTitle) {
        await fetchGameState();
    }
}, { immediate: true })
</script>

<style scoped>
.board {
    height: 100vh;
}

.hero {
    /* width: 100px; */
}
</style>
<template>
    <div v-if="gameOver.isGameOver" class="absolute inset-0 bg-black/75 flex items-center justify-center z-50">
        <div class="bg-white dark:bg-gray-800 rounded-2xl p-8 max-w-md mx-4 text-center shadow-2xl">
            <div class="mb-6">
                <div class="text-6xl mb-4">
                    {{ gameOver.winner === viewer ? '🎉' : '💀' }}
                </div>
                <h2 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                    {{ gameOver.winner === viewer ? 'Victory!' : 'Defeat!' }}
                </h2>
                <!-- <p class="text-lg text-gray-600 dark:text-gray-400">
                    {{ gameOver.winner === 'side_a' ? 'Side A' : 'Side B' }} wins the game!
                </p> -->
            </div>

            <!-- ELO Rating Changes (only for PvP games) -->
            <div v-if="eloChange" class="mb-6 p-4 bg-gray-100 dark:bg-gray-700 rounded-lg">
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                    ⚔️ Rating Changes
                </h3>
                <div class="space-y-2">
                    <!-- Winner -->
                    <div class="flex items-center justify-between p-2 bg-green-50 dark:bg-green-900/20 rounded">
                        <span class="font-medium text-gray-900 dark:text-white">
                            {{ eloChange.winner.display_name }}
                        </span>
                        <div class="flex items-center gap-2">
                            <span class="font-bold text-amber-600 dark:text-amber-400">{{ eloChange.winner.new_rating }}</span>
                            <span class="text-green-600 dark:text-green-400 font-bold">
                                [ {{ eloChange.winner.change > 0 ? '+' : '' }}{{ eloChange.winner.change }} ]
                            </span>
                        </div>
                    </div>

                    <!-- Loser -->
                    <div class="flex items-center justify-between p-2 bg-red-50 dark:bg-red-900/20 rounded">
                        <span class="font-medium text-gray-900 dark:text-white">
                            {{ eloChange.loser.display_name }}
                        </span>
                        <div class="flex items-center gap-2">
                            <span class="font-bold text-amber-600 dark:text-amber-400">{{ eloChange.loser.new_rating }}</span>
                            <span class="text-red-600 dark:text-red-400 font-bold">
                                [ {{ eloChange.loser.change }} ]
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="space-y-3">
                <router-link :to="{ name: 'Title', params: { slug: titleStore.titleSlug } }">
                    <button
                        class="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
                    >
                        Exit Game
                    </button>
                </router-link>

                <button
                    @click="handleReturnToGame"
                    class="w-full px-4 py-3 bg-gray-600 hover:bg-gray-700 text-white font-medium rounded-lg transition-colors"
                >
                    Return to Game
                </button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { useTitleStore } from '@/stores/title'
import type { Side, EloChange } from '../../../types/game'

const titleStore = useTitleStore()

interface GameOverState {
    isGameOver: boolean
    winner: Side | null
}

interface Props {
    gameOver: GameOverState
    viewer: Side | null
    eloChange?: EloChange
}

const props = defineProps<Props>()

const emit = defineEmits<{
    'close': []
}>()

const handleReturnToGame = () => {
    emit('close')
}
</script>
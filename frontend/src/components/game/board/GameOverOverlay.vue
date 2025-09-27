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
                <p class="text-lg text-gray-600 dark:text-gray-400">
                    {{ gameOver.winner === 'side_a' ? 'Side A' : 'Side B' }} wins the game!
                </p>
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
import type { Side } from '../../../types/game'

const titleStore = useTitleStore()

interface GameOverState {
    isGameOver: boolean
    winner: Side | null
}

interface Props {
    gameOver: GameOverState
    viewer: Side | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
    'close': []
}>()

const handleReturnToGame = () => {
    emit('close')
}
</script>
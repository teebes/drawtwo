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
                <button
                    @click="handleReturnToLobby"
                    class="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
                >
                    Return to Lobby
                </button>
                <button
                    @click="handlePlayAgain"
                    class="w-full px-4 py-3 bg-gray-600 hover:bg-gray-700 text-white font-medium rounded-lg transition-colors"
                >
                    Play Again
                </button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { Side } from '../../../types/game'

interface GameOverState {
    isGameOver: boolean
    winner: Side | null
}

interface Props {
    gameOver: GameOverState
    viewer: Side | null
}

const props = defineProps<Props>()
const router = useRouter()

const handleReturnToLobby = () => {
    router.push('/lobby')
}

const handlePlayAgain = () => {
    window.location.reload()
}
</script>
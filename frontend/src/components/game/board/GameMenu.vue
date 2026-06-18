<template>
    <div class="flex flex-col items-center justify-center space-y-8 my-8">
        <div
            v-if="nextGame"
            class="text-2xl cursor-pointer text-primary-400 hover:text-primary-300"
            @click="handleNextGame">
            Next Game
        </div>

        <div class="text-2xl cursor-pointer hover:text-gray-400" @click="handleClickUpdates">
            Updates
        </div>

        <div
            v-if="showExtendTime && !gameOver"
            class="text-2xl cursor-pointer hover:text-gray-400"
            @click="handleClickExtendTime">
            Extend Time
        </div>

        <div v-if="canEditTitle" class="text-2xl cursor-pointer hover:text-gray-400" @click="handleClickDebug">
            Debug
        </div>

        <div
            v-if="!gameOver"
            class="text-2xl cursor-pointer hover:text-red-400"
            @click="handleConcede">
            Concede
        </div>

        <div class="text-2xl cursor-pointer hover:text-gray-400" @click="handleExitGame">
            Exit Game
        </div>
    </div>
</template>

<script setup lang="ts">
import { useGameStore } from '@/stores/game'
import { useRouter } from 'vue-router'

const props = defineProps<{
    canEditTitle: boolean
    showExtendTime: boolean
    titleSlug: string | undefined
    gameOver: boolean
    nextGame?: {
        id: number
        type: 'pve' | 'ranked' | 'friendly' | 'intro'
        name: string
    } | null
}>()

const emit = defineEmits<{
    clickUpdates: []
    clickExtendTime: []
    clickDebug: []
}>()

const gameStore = useGameStore()
const router = useRouter()

const handleClickUpdates = () => {
    emit('clickUpdates')
}

const handleClickExtendTime = () => {
    emit('clickExtendTime')
}

const handleClickDebug = () => {
    emit('clickDebug')
}

const handleNextGame = () => {
    if (!props.nextGame || !props.titleSlug) return

    gameStore.disconnectWebSocket()
    router.push({
        name: 'Board',
        params: {
            slug: props.titleSlug,
            game_id: props.nextGame.id,
        },
    })
}

const handleConcede = () => {
    if (confirm('Are you sure you want to concede this game?')) {
        gameStore.concedeGame()
    }
}

const handleExitGame = () => {
    // Disconnect WebSocket intentionally before navigating
    gameStore.disconnectWebSocket()

    // Navigate to title page
    router.push({ name: 'Title', params: { slug: props.titleSlug } })
}
</script>

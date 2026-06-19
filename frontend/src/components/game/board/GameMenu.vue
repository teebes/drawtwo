<template>
    <div class="flex flex-col items-center justify-center space-y-8 my-8">
        <div
            v-if="nextGame"
            class="text-2xl cursor-pointer text-primary-400 hover:text-primary-300"
            @click="handleNextGame">
            Next Game
        </div>

        <div class="text-2xl cursor-pointer hover:text-gray-400" @click="handleClickUpdates">
            Log
        </div>

        <div class="text-2xl cursor-pointer hover:text-gray-400" @click="handleClickHowToPlay">
            How to Play
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

        <button
            v-if="!gameOver"
            type="button"
            class="appearance-none bg-transparent text-2xl cursor-pointer hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="concedeSubmitted"
            @click="handleConcede">
            Concede
        </button>

        <div class="text-2xl cursor-pointer hover:text-gray-400" @click="handleExitGame">
            Exit Game
        </div>
    </div>

    <BaseModal :show="showConcedeModal" @close="closeConcedeModal">
        <div class="p-6">
            <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
                Concede game?
            </h2>
            <p class="mt-3 text-sm text-gray-600 dark:text-gray-300">
                This will immediately end the game and count as a loss.
            </p>

            <div class="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <button
                    type="button"
                    class="ui-btn ui-btn-md ui-btn-secondary"
                    :disabled="concedeSubmitted"
                    @click="closeConcedeModal">
                    Cancel
                </button>
                <button
                    type="button"
                    class="ui-btn ui-btn-md ui-btn-danger"
                    :disabled="concedeSubmitted"
                    @click="confirmConcede">
                    {{ concedeSubmitted ? 'Conceding...' : 'Concede' }}
                </button>
            </div>
        </div>
    </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from '@/components/modals/BaseModal.vue'
import { useGameStore } from '@/stores/game'
import { ref, watch } from 'vue'
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
    clickHowToPlay: []
    clickExtendTime: []
    clickDebug: []
}>()

const gameStore = useGameStore()
const router = useRouter()
const showConcedeModal = ref(false)
const concedeSubmitted = ref(false)

const handleClickUpdates = () => {
    emit('clickUpdates')
}

const handleClickHowToPlay = () => {
    emit('clickHowToPlay')
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
    if (props.gameOver || concedeSubmitted.value) return
    showConcedeModal.value = true
}

const closeConcedeModal = () => {
    if (concedeSubmitted.value) return
    showConcedeModal.value = false
}

const confirmConcede = () => {
    if (props.gameOver || concedeSubmitted.value) return

    concedeSubmitted.value = true
    gameStore.concedeGame()
    showConcedeModal.value = false
}

const handleExitGame = () => {
    // Disconnect WebSocket intentionally before navigating
    gameStore.disconnectWebSocket()

    // Navigate to title page
    router.push({ name: 'Title', params: { slug: props.titleSlug } })
}

watch(
    () => props.gameOver,
    (isGameOver) => {
        if (isGameOver) {
            showConcedeModal.value = false
        }
    }
)
</script>

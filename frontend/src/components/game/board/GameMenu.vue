<template>
    <div class="flex flex-col items-center justify-center space-y-8 my-8">
        <div class="text-2xl cursor-pointer hover:text-gray-400" @click="handleClickUpdates">
            Updates
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

        <div class="text-2xl">
            <router-link :to="{ name: 'Title', params: { slug: titleSlug } }"
                         class="hover:text-gray-400">
                Exit Game
            </router-link>
        </div>
    </div>
</template>

<script setup lang="ts">
import { useGameStore } from '@/stores/game'

const props = defineProps<{
    canEditTitle: boolean
    titleSlug: string | undefined
    gameOver: boolean
}>()

const emit = defineEmits<{
    clickUpdates: []
    clickDebug: []
}>()

const gameStore = useGameStore()

const handleClickUpdates = () => {
    emit('clickUpdates')
}

const handleClickDebug = () => {
    emit('clickDebug')
}

const handleConcede = () => {
    if (confirm('Are you sure you want to concede this game?')) {
        gameStore.concedeGame()
    }
}
</script>

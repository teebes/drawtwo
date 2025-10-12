<template>
    <div class="flex-1 min-h-0 p-6">
        <div class="flex flex-col space-y-6">
            <div class="space-y-2">
                <h3 class="text-lg font-semibold text-gray-300">Game State</h3>
                <a
                    :href="stateEndpoint"
                    target="_blank"
                    class="block text-blue-400 hover:text-blue-300 underline break-all text-sm"
                >
                    {{ stateEndpoint }}
                </a>
            </div>

            <div class="space-y-2">
                <h3 class="text-lg font-semibold text-gray-300">Queue</h3>
                <a
                    :href="queueEndpoint"
                    target="_blank"
                    class="block text-blue-400 hover:text-blue-300 underline break-all text-sm"
                >
                    {{ queueEndpoint }}
                </a>
            </div>

            <div class="space-y-2">
                <h3 class="text-lg font-semibold text-gray-300">Advance Queue</h3>
                <button
                    @click="handleAdvanceQueue"
                    class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
                >
                    Advance Queue
                </button>
                <div v-if="advanceSuccess" class="text-sm mt-2" :class="advanceSuccess.includes('Error') ? 'text-red-400' : 'text-green-400'">
                    {{ advanceSuccess }}
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import axios from '../../../config/api'

const props = defineProps<{
    gameId: string
}>()

const advanceSuccess = ref<string | null>(null)

// Debug endpoint URLs
const stateEndpoint = computed(() => `${axios.defaults.baseURL}/gameplay/games/${props.gameId}/?format=json`)
const queueEndpoint = computed(() => `${axios.defaults.baseURL}/gameplay/games/${props.gameId}/queue/?format=json`)
const advanceEndpoint = computed(() => `${axios.defaults.baseURL}/gameplay/games/${props.gameId}/advance/`)

const handleAdvanceQueue = async () => {
    try {
        await axios.post(advanceEndpoint.value)
        advanceSuccess.value = "Queue advanced successfully!"
        setTimeout(() => {
            advanceSuccess.value = null
        }, 3000)
    } catch (error) {
        console.error('Error advancing queue:', error)
        advanceSuccess.value = "Error advancing queue"
        setTimeout(() => {
            advanceSuccess.value = null
        }, 3000)
    }
}
</script>

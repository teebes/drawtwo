<template>
    <div ref="container" class="flex flex-col h-full border-gray-700 overflow-y-auto">
        <div v-for="(group, index) in turnGroups" :key="index" class="border-gray-700" :class="{ 'border-b': index < turnGroups.length - 1 }">
            <!-- Turn Header -->
            <div class="text-center py-2 text-gray-400 font-bold text-sm uppercase tracking-wider bg-gray-900/30">
                {{ group.label }}
            </div>

            <!-- Updates in this turn -->
            <div class="flex flex-col pb-2">
                <div class="flex items-center justify-center py-1 px-2"
                     v-for="update in group.updates" :key="update.timestamp">
                    <Update :update="update" :hide-source="update.side === group.side" />
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick, onMounted } from 'vue'
import Update from './Update.vue'
import { useGameStore } from '@/stores/game'

const props = defineProps<{
    updates: any[]
}>()

const gameStore = useGameStore()
const container = ref<HTMLElement | null>(null)

interface TurnGroup {
    side: string
    updates: any[]
    label: string
}

const turnGroups = computed(() => {
    const groups: TurnGroup[] = []
    let currentUpdates: any[] = []

    // We need to track whose turn it is for the current group.
    // If we have existing groups, the next one is the other player.
    // If we are starting, we look at the first update.
    let currentSide: string | null = null

    for (const update of props.updates) {
        if (!currentSide) {
            // Try to determine side from the update itself if starting a new group
            currentSide = update.side
        }

        currentUpdates.push(update)

        if (update.type === 'update_end_turn') {
            // End of a turn group
            // update.side is the player who ended the turn
            const side = update.side
            groups.push({
                side: side,
                updates: [...currentUpdates],
                label: getTurnLabel(side, Math.floor(groups.length / 2) + 1)
            })
            currentUpdates = []
            currentSide = null // Reset for next group
        }
    }

    // Handle any remaining updates (current ongoing turn)
    if (currentUpdates.length > 0) {
        // Infer side for the incomplete group
        let side = currentSide
        if (!side) {
            // If we couldn't determine side from updates (unlikely as they have side),
            // or if we want to enforce alternating turns logic:
            if (groups.length > 0) {
                const lastSide = groups[groups.length - 1].side
                side = lastSide === 'side_a' ? 'side_b' : 'side_a'
            } else {
                // First group, fallback to update side or active
                side = currentUpdates[0].side || 'side_a'
            }
        }

        groups.push({
            side: side!,
            updates: [...currentUpdates],
            label: getTurnLabel(side!, Math.floor(groups.length / 2) + 1)
        })
    }

    return groups
})

function getTurnLabel(side: string, turnNumber: number) {
    const hero = gameStore.gameState.heroes[side]
    const name = (gameStore.viewer === side) ? "You" : (hero ? hero.name : "Enemy")
    return `Turn ${turnNumber} - ${name}`
}

const scrollToBottom = async () => {
    await nextTick()
    if (container.value) {
        container.value.scrollTop = container.value.scrollHeight
    }
}

onMounted(scrollToBottom)

// Auto-scroll to bottom when updates change
watch(() => props.updates.length, scrollToBottom)
</script>

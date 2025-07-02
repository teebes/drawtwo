<template>
  <div class="flex items-center">
    <div class="flex space-x-1 max-w-full overflow-x-auto">
      <div v-for="cardId in handCards.slice(0, maxCards)" :key="cardId"
        class="flex-shrink-0 w-16 h-20 bg-gradient-to-b from-amber-400 to-amber-600 rounded border border-amber-300/50 shadow-sm flex flex-col p-1">

        <!-- Cost (top-left corner) -->
        <div class="flex justify-between items-start">
          <div class="bg-blue-600 text-white text-xs font-bold rounded-full w-4 h-4 flex items-center justify-center">
            {{ getCard(cardId)?.cost || 0 }}
          </div>
        </div>

        <!-- Card Name (center, small font, wrapping) -->
        <div class="flex-1 flex items-center justify-center">
          <div class="text-amber-900 text-[0.6rem] font-semibold text-center leading-tight break-words max-w-full">
            {{ getCardName(cardId) }}
          </div>
        </div>

        <!-- Attack/Health (bottom) -->
        <div class="flex justify-between items-end">
          <div class="bg-red-600 text-white text-xs font-bold rounded-full w-4 h-4 flex items-center justify-center">
            {{ getCard(cardId)?.attack || 0 }}
          </div>
          <div class="bg-green-600 text-white text-xs font-bold rounded-full w-4 h-4 flex items-center justify-center">
            {{ getCard(cardId)?.health || 0 }}
          </div>
        </div>
      </div>

      <div v-if="handCards.length === 0" class="text-gray-400 text-xs py-2">
        No cards
      </div>
      <div v-if="handCards.length > maxCards" class="flex-shrink-0 text-gray-400 text-xs py-2">
        +{{ handCards.length - maxCards }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CardInPlay } from '../../types/game'

interface Props {
  handCards: string[]
  cards: Record<string, CardInPlay>
  maxCards?: number
}

const props = withDefaults(defineProps<Props>(), {
  maxCards: 4
})

// Extract maxCards with default value to avoid undefined issues
const maxCards = props.maxCards ?? 4

const getCard = (cardId: string): CardInPlay | undefined => {
  return props.cards[cardId]
}

const getCardName = (cardId: string): string => {
  const card = getCard(cardId)
  if (!card) return 'Unknown'

  // Convert template_slug to a readable name
  return card.template_slug
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}
</script>

<style scoped>
/* Custom scrollbar for horizontal card overflow */
.overflow-x-auto::-webkit-scrollbar {
  height: 2px;
}

.overflow-x-auto::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 1px;
}

.overflow-x-auto::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 1px;
}

.overflow-x-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}
</style>
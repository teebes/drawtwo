<template>
  <div class="flex items-center">
    <div class="flex space-x-1 max-w-full overflow-x-auto">
      <div v-for="cardId in handCards.slice(0, maxCards)" :key="cardId"
        @click="handleCardClick(cardId)"
        :class="[
          'flex-shrink-0 w-16 h-20 bg-gradient-to-b from-amber-400 to-amber-600 rounded shadow-sm flex flex-col p-1 transition-all duration-200',
          isPlayable(cardId) ? 'border-2 border-blue-500 cursor-pointer' : 'border border-amber-300/50',
          selectedCard === cardId ? '-translate-y-6' : '',
          isPlayable(cardId) && selectedCard !== cardId ? 'hover:-translate-y-1' : ''
        ]">

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
import { ref } from 'vue'
import type { CardInPlay } from '../../types/game'

interface Props {
  handCards: string[]
  cards: Record<string, CardInPlay>
  manaPool: number
  manaUsed: number
  isMainPhase: boolean
  maxCards?: number
}

const props = withDefaults(defineProps<Props>(), {
  maxCards: 4
})

const emit = defineEmits<{
  'card-selected': [cardId: string | null]
}>()

// Track selected card locally
const selectedCard = ref<string | null>(null)

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

const isPlayable = (cardId: string): boolean => {
  if (!props.isMainPhase) return false

  const card = getCard(cardId)
  if (!card) return false

  // Cards in hand shouldn't be exhausted, but check just in case
  // if (card.exhausted) return false

  // Check if we have enough mana to play this card
  const availableMana = props.manaPool - props.manaUsed
  return card.cost <= availableMana
}

const handleCardClick = (cardId: string) => {
  if (!isPlayable(cardId)) return

  // Toggle selection
  if (selectedCard.value === cardId) {
    selectedCard.value = null
    emit('card-selected', null)
  } else {
    selectedCard.value = cardId
    emit('card-selected', cardId)
  }
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
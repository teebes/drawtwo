<template>
  <BaseModal :show="show" @close="$emit('close')">
    <div class="p-6">
      <!-- Header -->
      <div class="mb-6">
        <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
          {{ title }}
        </h2>
        <p v-if="subtitle" class="mt-1 text-sm text-gray-600 dark:text-gray-400">
          {{ subtitle }}
        </p>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="py-8 text-center">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-3"></div>
        <p class="text-gray-600 dark:text-gray-400">Loading decks...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="decks.length === 0" class="py-8 text-center">
        <div class="flex h-16 w-16 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800 mx-auto mb-4">
          <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
          </svg>
        </div>
        <p class="text-gray-600 dark:text-gray-400 mb-4">You don't have any decks yet.</p>
        <slot name="empty-action"></slot>
      </div>

      <!-- Deck List -->
      <div v-else class="space-y-2 max-h-[400px] overflow-y-auto">
        <button
          v-for="deck in decks"
          :key="deck.id"
          @click="selectDeck(deck)"
          :class="[
            'w-full flex items-center justify-between rounded-lg border-2 p-4 transition-all text-left',
            selectedDeck?.id === deck.id
              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
              : 'border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-700 hover:bg-gray-50 dark:hover:bg-gray-800'
          ]"
        >
          <div class="flex items-center space-x-3">
            <!-- Hero Avatar -->
            <div
              class="relative w-12 h-12 rounded-lg overflow-hidden bg-gray-200 dark:bg-gray-700 flex items-center justify-center border border-gray-300 dark:border-gray-600"
            >
              <img
                v-if="deck.hero.art_url"
                :src="deck.hero.art_url"
                :alt="deck.hero.name"
                class="h-full w-full object-cover"
              />
              <span v-else class="text-lg font-semibold text-primary-600">
                {{ deck.hero.name.charAt(0) }}
              </span>
            </div>
            <div>
              <div class="font-medium text-gray-900 dark:text-white">{{ deck.name }}</div>
              <div class="text-sm text-gray-600 dark:text-gray-400">
                {{ deck.hero.name }} • {{ deck.card_count }} cards
              </div>
            </div>
          </div>
          <!-- Selected Check -->
          <div v-if="selectedDeck?.id === deck.id" class="text-primary-600 dark:text-primary-400">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
          </div>
        </button>
      </div>

      <!-- Actions -->
      <div class="mt-6 flex justify-end gap-3">
        <button
          @click="$emit('close')"
          class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          Cancel
        </button>
        <button
          @click="confirm"
          :disabled="!selectedDeck || confirming"
          :class="[
            'rounded-lg px-4 py-2 text-sm font-medium transition-colors',
            selectedDeck && !confirming
              ? 'bg-primary-600 text-white hover:bg-primary-700'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed dark:bg-gray-700 dark:text-gray-500'
          ]"
        >
          {{ confirming ? 'Confirming...' : confirmText }}
        </button>
      </div>
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import BaseModal from './BaseModal.vue'

interface DeckData {
  id: number
  name: string
  hero: {
    id: number
    name: string
    slug: string
    art_url?: string | null
  }
  card_count: number
}

const props = withDefaults(defineProps<{
  show: boolean
  title?: string
  subtitle?: string
  confirmText?: string
  decks: DeckData[]
  loading?: boolean
  confirming?: boolean
}>(), {
  title: 'Select a Deck',
  confirmText: 'Confirm',
  loading: false,
  confirming: false
})

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'confirm', deck: DeckData): void
}>()

const selectedDeck = ref<DeckData | null>(null)

// Reset selection when modal opens
watch(() => props.show, (newShow) => {
  if (newShow) {
    selectedDeck.value = null
  }
})

const selectDeck = (deck: DeckData) => {
  selectedDeck.value = deck
}

const confirm = () => {
  if (selectedDeck.value) {
    emit('confirm', selectedDeck.value)
  }
}
</script>

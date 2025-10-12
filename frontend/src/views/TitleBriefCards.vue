<template>
  <div class="template-page">
    <main class="flex-1" v-if="cardsLoading">
      <div class="text-center py-12">
        <p class="text-gray-600 dark:text-gray-400">Loading cards...</p>
      </div>
    </main>

    <main class="flex-1" v-else>
      <!-- Content goes here -->
      <section class="py-4">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <!-- Filter Controls -->
          <div class="mb-6 flex gap-4">
            <!-- Faction Filter -->
            <div class="flex flex-col">
              <label for="faction-filter" class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Faction
              </label>
              <select
                id="faction-filter"
                v-model="selectedFaction"
                class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Factions</option>
                <option value="common">Common</option>
                <option v-for="faction in availableFactions" :key="faction" :value="faction">
                  {{ faction.toUpperCase() }}
                </option>
              </select>
            </div>

            <!-- Card Type Filter -->
            <div class="flex flex-col">
              <label for="type-filter" class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Type
              </label>
              <select
                id="type-filter"
                v-model="selectedType"
                class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All</option>
                <option value="creature">Creature</option>
                <option value="spell">Spell</option>
              </select>
            </div>
          </div>
                        <router-link
              v-for="card in filteredCards"
              :key="card.slug"
              :to="{ name: 'CardEdit', params: { slug: route.params.slug, cardSlug: card.slug } }"
              class="block py-2 border-b border-b-black hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer"
            >
              {{ card.cost }} - {{ card.attack }} - {{ card.health }} -
              <span v-if="card.faction">[ {{ card.faction.toLocaleUpperCase() }} ]</span>
              <span v-if="card.card_type == 'spell'">[ SPELL ]</span>
              {{ card.name }}
              <span v-if="card.traits && card.traits.length">
                [
                <span v-for="(trait, idx) in card.traits" :key="trait.slug">
                  <span v-if="idx !== 0"> | </span>
                  {{ trait.name.toUpperCase() }}
                  <span v-if="trait.data && Object.keys(trait.data).length">
                    (
                    <span v-for="(value, key, dIdx) in trait.data" :key="key">
                      <span v-if="dIdx !== 0">, </span>{{ key }}: {{ value }}
                    </span>
                    )
                  </span>
                </span>
                ]
              </span>
            </router-link>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { useRoute } from 'vue-router'
import type { Card } from '../types/card'

const route = useRoute()
const cards = ref<Card[]>([])
const cardsLoading = ref(false)
const error = ref(null)

// Filter state
const selectedFaction = ref('common')
const selectedType = ref('creature')

const fetchCards = async (): Promise<void> => {

  try {
    cardsLoading.value = true
    const slug = route.params.slug as string
    const response = await axios.get(`/titles/${slug}/cards/`)
    cards.value = response.data || []
  } catch (err) {
    console.error('Error fetching cards:', err)
    // Don't set error for cards if title loaded successfully
    // Just log it and show empty state
  } finally {
    cardsLoading.value = false
  }
}

// Computed properties for filtering
const availableFactions = computed(() => {
  const factions = new Set<string>()
  cards.value.forEach(card => {
    if (card.faction) {
      factions.add(card.faction)
    }
  })
  return Array.from(factions).sort()
})

const filteredCards = computed(() => {
  return cards.value.filter(card => {
    // Faction filter
    if (selectedFaction.value) {
      if (selectedFaction.value === 'common' && card.faction !== null) {
        return false
      }
      if (selectedFaction.value !== 'common' && card.faction !== selectedFaction.value) {
        return false
      }
    }

    // Type filter
    if (selectedType.value && card.card_type !== selectedType.value) {
      return false
    }

    return true
  })
})

const getTraits = (card: Card) => {

}

onMounted(async () => {
  await fetchCards()
})
</script>

<style scoped>
.template-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
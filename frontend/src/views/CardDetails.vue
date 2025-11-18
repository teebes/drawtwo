<template>
  <div v-if="!loading && card" class="card-details bg-gray-50 dark:bg-gray-900 flex flex-col h-full">

    <!-- Card Name -->
    <section class="relative bg-gray-300 overflow-hidden h-24 flex flex-shrink-0 items-center justify-center space-x-6">
      <button
        type="button"
        @click="handleBack"
        class="absolute left-2 top-4 -translate-y-1/2 inline-flex items-center text-sm font-medium text-gray-600 hover:text-gray-800 dark:text-gray-700 dark:hover:text-gray-500"
      >
        ← Back
      </button>
      <h1 class="font-display text-4xl font-bold dark:text-gray-900">{{ card.name }}</h1>
      <router-link
        v-if="canEditTitle"
        :to="{ name: 'CardEdit', params: { slug: titleSlug, cardSlug } }"
        class="absolute right-6 top-1/2 -translate-y-1/2"
      >
        <GameButton variant="secondary" size="xs">
          Edit
        </GameButton>
      </router-link>
    </section>

    <!-- Card Info -->
    <section class="mx-auto max-w-xl w-full flex flex-col p-4 flex-grow sm:flex-row-reverse sm:mt-8 sm:gap-8">

        <div class="mb-4">
          <!-- Card Type / Traits -->
          <div class="text-gray-400 mb-4">
            {{ cardType }}
            <span v-if="card.traits.length > 0" class="ml-4">
            [ {{ card.traits.map(t => t.type.toUpperCase()).join(', ') }} ]
            </span>
          </div>

          <!-- Cost / Attack / Health -->
          <dl class="stats w-[6rem]">
            <dt class="text-blue-500">Cost</dt><dd class="text-blue-500">2</dd>
            <dt class="text-red-500">Attack</dt><dd class="text-red-500">1</dd>
            <dt class="text-green-500">Health</dt><dd class="text-green-500">3</dd>
          </dl>

          <!-- Card Description -->
          <div class="rounded-xl border border-gray-300 p-4 mt-8">
            {{ card.description }}
          </div>
        </div>

        <div class="w-48 mx-auto p-1">
          <GameCard :card="card" />
        </div>

    </section>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../config/api'
import GameCard from '../components/game/GameCard.vue'
import GameButton from '../components/ui/GameButton.vue'
import { useAuthStore } from '../stores/auth'
import { useTitleStore } from '../stores/title'
import type { Card } from '../types/card'

const route = useRoute()
const router = useRouter()
const titleSlug = route.params.slug as string
const cardSlug = route.params.cardSlug as string

const card = ref<Card | null>(null)
const loading = ref<boolean>(true)

const cardType = computed(() => {
  return card.value?.card_type === 'creature' ? 'Creature' : 'Spell'
})

const authStore = useAuthStore()
const titleStore = useTitleStore()

const canEditTitle = computed(() => {
  return authStore.isAuthenticated && titleStore.currentTitle?.can_edit === true
})

// Methods
const handleBack = (): void => {
  const historyState = window.history.state as { back?: string | null } | null
  if (historyState?.back) {
    router.back()
  } else {
    router.push({ name: 'TitleCards', params: { slug: titleSlug } })
  }
}

const fetchCard = async (): Promise<void> => {
  try {
    const response = await axios.get(`/titles/${titleSlug}/cards/${cardSlug}/`)
    card.value = response.data
  } catch (err: any) {
    console.error('Error fetching card:', err)
  } finally {
    loading.value = false
  }
}


onMounted(() => {
  fetchCard()
})
</script>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: auto max-content; /* label grows, value hugs content */
  column-gap: 0.75rem;
  row-gap: 0.25rem;
  margin: 0;

  dt, dd { margin: 0; }
  dd { text-align: right; }
  font-variant-numeric: tabular-nums;
}
</style>
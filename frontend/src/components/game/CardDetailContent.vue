<template>
  <div class="card-detail-content flex flex-col h-full bg-gray-50 dark:bg-gray-900">

    <!-- Card Name Header -->
    <section class="relative bg-gray-300 dark:bg-gray-800 overflow-hidden h-24 flex flex-shrink-0 items-center justify-center space-x-6">
       <slot name="back-button"></slot>
      <h1 class="font-display text-4xl font-bold dark:text-gray-100">{{ card.name }}</h1>

      <div v-if="canEdit && titleSlug" class="absolute right-6 top-1/2 -translate-y-1/2">
        <router-link
            :to="{ name: 'CardEdit', params: { slug: titleSlug, cardSlug: card.slug } }"
        >
            <GameButton variant="secondary" size="xs">
            Edit
            </GameButton>
        </router-link>
      </div>
    </section>

    <!-- Card Info -->
    <section class="mx-auto max-w-xl w-full flex flex-col p-4 flex-grow sm:flex-row-reverse sm:mt-8 sm:gap-8">

        <div class="mb-4 flex-grow">
          <!-- Card Type / Traits -->
          <div class="text-gray-500 dark:text-gray-400 mb-4 font-medium">
            {{ cardType }}
            <span v-if="card.traits && card.traits.length > 0" class="ml-4">
            [ {{ card.traits.map(t => t.type.toUpperCase()).join(', ') }} ]
            </span>
          </div>

          <!-- Cost / Attack / Health -->
          <dl class="stats w-[6rem] text-lg">
            <dt class="text-blue-600 dark:text-blue-400 font-bold">Cost</dt>
            <dd class="text-blue-600 dark:text-blue-400 font-bold">{{ card.cost }}</dd>

            <template v-if="card.card_type === 'creature'">
                <dt class="text-red-600 dark:text-red-400 font-bold">Attack</dt>
                <dd class="text-red-600 dark:text-red-400 font-bold">{{ card.attack }}</dd>
                <dt class="text-green-600 dark:text-green-400 font-bold">Health</dt>
                <dd class="text-green-600 dark:text-green-400 font-bold">{{ card.health }}</dd>
            </template>
          </dl>

          <!-- Card Description -->
          <div class="rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 mt-8 text-gray-900 dark:text-gray-100 shadow-sm text-lg">
            {{ card.description }}
          </div>
        </div>

        <div class="w-48 mx-auto p-1 flex-shrink-0">
          <GameCard :card="card" />
        </div>

    </section>

  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Card } from '../../types/card'
import GameCard from './GameCard.vue'
import GameButton from '../ui/GameButton.vue'

const props = defineProps<{
  card: Card
  titleSlug?: string
  canEdit?: boolean
}>()

const cardType = computed(() => {
  return props.card.card_type === 'creature' ? 'Creature' : 'Spell'
})
</script>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: auto max-content; /* label grows, value hugs content */
  column-gap: 0.75rem;
  row-gap: 0.25rem;
  margin: 0;
}
.stats dt, .stats dd { margin: 0; }
.stats dd { text-align: right; }
.stats { font-variant-numeric: tabular-nums; }
</style>

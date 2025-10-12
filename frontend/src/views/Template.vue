<template>
  <div class="template-page flex flex-col">
    <main class="flex-1 flex items-center justify-center">
      <!-- Content goes here -->
      <section class="py-16">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="text-center">
            <CollectionCard
              :card="card"
              heightMode="fixed"
              height="md"
            />
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import CollectionCard from '../components/game/CollectionCard.vue'
import type { Card } from '../types/card'

const card: Card = {
  id: 1,
  slug: 'test-card',
  name: 'Test Card',
  description: 'This is a test card',
  card_type: 'creature',
  cost: 1,
  attack: 1,
  health: 1,
  traits: []
}


</script>

<style scoped>
.template-page {
  height: calc(100vh - 4rem); /* Subtract header height (64px/4rem) */
  display: flex;
  flex-direction: column;
}
</style>
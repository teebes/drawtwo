<template>
  <div class="template-page flex flex-col">
    <main class="flex-1 flex items-center justify-center">
        <div style="width: 200px">
          <GameCard :card="card" title-slug="archetype"/>
        </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import type { Card } from '../types/card'
import GameCard from '../components/game/GameCard.vue'

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
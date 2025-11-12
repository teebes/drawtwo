<template>
  <div class="template-page flex flex-col">
    <!-- <div class="w-12">
    <GameCard :card="card" title-slug="archetype" compact in_lane/>
    </div> -->
     <div class="w-20 h-28 border-2 border-gray-900 bg-gray-300 text-gray-900 rounded-xl relative">
      <div class="absolute top-0 left-0 right-0 bottom-0 z-index-10 bg-gray-900/70"></div>
      C
     </div>
  </div>
</template>

<script setup lang="ts">
import GameCard from '../components/game/GameCard.vue'
import type { Card } from '../types/card'

const card: Card = {
  id: 1,
  slug: 'mongoose',
  name: 'Mongoose',
  description: 'This is a test card',
  card_type: 'creature',
  cost: 1,
  attack: 1,
  health: 1,
  traits: [],
  art_url: 'https://assets.drawtwo.com/titles/archetype/cards/grenade.webp'
}


</script>

<style scoped>
.template-page {
  display: flex;
  flex-direction: column;
}
</style>
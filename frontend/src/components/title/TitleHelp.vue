<template>
  <div class="title-help mx-auto max-w-2xl space-y-8 px-4 py-8">
    <h1 v-if="showTitle" class="text-center">How to Play</h1>

    <div>A game opposes two heroes, and ends when a hero's health reaches 0 or when all cards in the deck are drawn.</div>

    <!-- Hero Board-->
    <div class="mx-auto flex w-full max-w-[320px] flex-col border border-gray-700">
      <!-- Opponent -->
      <div class="flex h-24 border-b border-gray-700">
        <!-- Opponent Avatar-->
        <div class="relative h-full w-24 border-r border-gray-700 bg-gray-500">
          <img src="https://assets.drawtwo.com/titles/archetype/heroes/healer.webp"
               alt="Healer"
               class="h-full w-full object-cover"/>
          <div class="absolute inset-0 z-10 flex items-center justify-center bg-black/50">
            <div class="font-bold text-white">20</div>
          </div>
        </div>

        <div class="flex flex-1 items-center justify-center space-x-2">
          <span class="text-2xl">←</span>
          <span>Opponent Hero</span>
        </div>
      </div>

      <!-- Middle -->
      <div class="flex h-[300px] flex-col items-center justify-center space-y-8 px-4">
        <div>The first player whose hero's health reaches 0 loses the game.</div>
        <div>
          The <div class="relative top-[0.4em] mx-1 inline-block h-6 w-6 border-4 border-primary-500"></div> border around the hero portrait indicates whose turn it is.
        </div>
      </div>

      <!-- Viewer -->
      <div class="flex h-24 border-t border-gray-700">
        <!-- Viewer Avatar-->
        <div class="relative h-full w-24 border-r border-gray-700 bg-gray-500">
          <img src="https://assets.drawtwo.com/titles/archetype/heroes/berserker.webp"
               alt="Berserker"
               class="h-full w-full object-cover">
          <div class="absolute inset-0 z-10 flex items-center justify-center bg-black/50">
            <div class="font-bold text-white">20</div>
          </div>
          <div class="pointer-events-none absolute inset-0 z-20 border-4 border-primary-500"></div>
        </div>

        <div class="flex flex-1 items-center justify-center space-x-2">
          <span class="text-2xl">←</span>
          <span>Own Hero</span>
        </div>
      </div>
    </div>

    <div>Players start with 3 cards and 0 energy. Each turn, all players gain 1 energy, up to 10.</div>

    <div>Cards have energy cost, and to play it, the player must have enough energy to pay for it.</div>

    <GameCard :card="brute" class="mx-auto w-48" />

    <div>The card above is a creature, which means that once played it will become a creature on the board, with attack and health. The three values mean:</div>

    <div class="mx-auto w-48 space-y-2">
      <div class="text-secondary-500">3 - Energy cost to play this card.</div>
      <div class="text-red-500">4 - Attack damage dealt when attacking with this creature.</div>
      <div class="text-green-500">5 - Health of the creature, when this reaches 0 the creature is destroyed.</div>
    </div>

    <div>Creatures deal physical damage, and whenever they receive physical damage they counterattack with their own attack damage.</div>

    <div>Spell cards, on the other hand, have neither attack nor health, and their effects are immediately executed and set to the discard pile.</div>

    <GameCard :card="zap" class="mx-auto w-48" details />

    <div>Unlike physical damage, spell damage does not trigger counter attacks, and it is not affected by the Taunt trait.</div>

    <div>The upper-left hand corner of the card shows one of the card's traits, in this case On Play.</div>

    <div>A trait is a special ability that a card can have. Possible traits are:</div>

    <div class="flex">
      <div class="card-badge mr-4">📣</div>
      <div>On Play - effect is executed when the card is played.</div>
    </div>

    <div class="flex">
      <div class="card-badge mr-4">💀</div>
      <div>On Death - effect is executed when the creature dies.</div>
    </div>

    <div class="flex">
      <div class="card-badge mr-4">👁️</div>
      <div>Stealth - creature cannot be directly targeted until it attacks.</div>
    </div>

    <div class="flex">
      <div class="card-badge mr-4">🛡️</div>
      <div>Taunt - creature must be attacked before other targets.</div>
    </div>

    <div class="flex">
      <div class="card-badge mr-4">🏹</div>
      <div>Ranged - creature can attack without taking counterattack damage.</div>
    </div>

    <div class="flex">
      <div class="card-badge mr-4">⚔️</div>
      <div>Charge - creature can attack immediately when played.</div>
    </div>

    <div class="flex">
      <div class="card-badge mr-4">⭐</div>
      <div>Unique - only one copy of this card can exist in your deck.</div>
    </div>

    <h2 class="mt-8 text-center">Misc Rules</h2>

    <div>If a deck runs out of cards and a card needs to be drawn, the player out of cards loses the game.</div>

    <div>When creatures are first played, they are in exhausted state. The exhausted state is removed at the end of each turn. A creature that is exhausted cannot attack.</div>

    <div>Taunt only blocks physical damage. Spell damage will bypass it.</div>

    <div>Using the Remove spell will bypass the On Death trait on the removed card.</div>

    <div>Silence removes all traits from an active enemy creature without changing its stats.</div>

    <div>When a player goes second, they start with an extra Power-Up card in their hand, which if used gives them 1 extra energy for the remainder of the turn.</div>
  </div>
</template>

<script setup lang="ts">
import GameCard from '../game/GameCard.vue'
import type { CardInPlay } from '../../types/game'

withDefaults(defineProps<{
  showTitle?: boolean
}>(), {
  showTitle: true,
})

const brute: CardInPlay = {
  card_type: 'creature',
  card_id: '1',
  template_slug: 'brute',
  name: 'Brute',
  description: '',
  attack: 4,
  health: 5,
  cost: 3,
  art_url: 'https://assets.drawtwo.com/titles/archetype/cards/brute.webp',
  exhausted: false,
  traits: [],
}

const zap: CardInPlay = {
  card_type: 'spell',
  card_id: '1',
  template_slug: 'zap',
  name: 'Zap',
  description: 'Deal 2 damage to an enemy.',
  attack: 0,
  health: 0,
  cost: 1,
  art_url: 'https://assets.drawtwo.com/titles/archetype/cards/zap.webp',
  exhausted: false,
  traits: [
    {
      type: 'battlecry',
      actions: [
        {
          action: 'damage',
          amount: 1,
          target: 'enemy',
          scope: 'single',
          damage_type: 'spell',
        }
      ]
    }
  ],
}
</script>

<style scoped>
.card-badge {
  @apply relative -top-1 z-20 flex h-8 w-8 items-center justify-center rounded-full border border-gray-900 bg-white text-white shadow-lg;
}
</style>

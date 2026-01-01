<template>
  <div class="howto max-w-2xl mx-auto px-4 space-y-8 py-8">
    <h1 class="text-center">How to Play</h1>

    <div>A game opposes two heroes, and ends when a hero's health reaches 0 or when all cards in the deck are drawn.</div>

    <!-- Hero Board-->
    <div class="flex flex-col border border-gray-700 w-[320px] mx-auto">
      <!-- Opponent -->
      <div class="h-24 border-b border-gray-700 flex">
        <!-- Opponent Avatar-->
        <div class="w-24 bg-gray-500 h-full border-r border-gray-700 relative">
          <img src="https://assets.drawtwo.com/titles/archetype/heroes/healer.webp"
               alt="Healer"
               class="w-full h-full object-cover"/>
          <div class="absolute inset-0 bg-black/50 flex items-center justify-center z-10">
            <div class="text-white font-bold">20</div>
          </div>
        </div>

        <div class="flex flex-1 items-center justify-center space-x-2">
          <span class="text-2xl">←</span>
          <span>Opponent Hero</span>
        </div>
      </div>

      <!-- middle -->
      <div class="h-[300px] flex flex-col items-center justify-center space-y-8 px-4">
        <div>The first player whose hero's health reaches 0 loses the game.</div>
        <div>
          The <div class="inline-block border-4 border-primary-500 w-6 h-6 relative top-[0.4em] mx-1"></div> border around the hero portrait indicates whose turn it is.
        </div>
      </div>

      <!-- Viewer -->
      <div class="h-24 border-t border-gray-700 flex">
        <!-- Viewer Avatar-->
        <div class="w-24 bg-gray-500 h-full border-r border-gray-700 relative">
          <img src="https://assets.drawtwo.com/titles/archetype/heroes/berserker.webp"
               alt="Berserker"
               class="w-full h-full object-cover"></img>
          <div class="absolute inset-0 bg-black/50 flex items-center justify-center z-10">
            <div class="text-white font-bold">20</div>
          </div>
          <div class="absolute inset-0 border-4 border-primary-500 z-20 pointer-events-none"></div>
        </div>

        <div class="flex flex-1 items-center justify-center space-x-2">
          <span class="text-2xl">←</span>
          <span>Own Hero</span>
        </div>

      </div>
    </div>

    <div>Players start with 3 cards and 0 energy. Each turn, all players gain 1 energy, up to 10.</div>

    <div>Cards have energy cost, and to play it, the player must have enough energy to pay for it.</div>

    <GameCard :card="brute" class="w-48 mx-auto" />

    <div>The card above is a creature, which means that once played it will become a creature on the board, with attack and health. The three values mean:</div>

    <div class="w-48 mx-auto space-y-2">
      <div class="text-secondary-500">3 - Energy cost to play this card.</div>
      <div class="text-red-500">4 - Attack damage dealt when attacking with this creature.</div>
      <div class="text-green-500">5 - Health of the creature, when this reaches 0 the creature is destroyed.</div>
    </div>

    <div>Creatures deal physical damage, and whenever they receive physical damage they counterattack with their own attack damage.</div>

    <div>Spell cards, on the other hand, have neither attack nor health, and their effects are immediately executed and set to the discard pile.</div>

    <GameCard :card="zap" class="w-48 mx-auto" details/>

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

    <h2 class="text-center mt-8">Misc Rules</h2>

    <div>When creatures are first played, they are in exhausted state. The exhausted state is removed at the end of each turn. A creature that is exhausted cannot attack.</div>

    <div>Taunt only blocks physical damage. Spell damage will bypass it.</div>

    <div>Using the Remove spell will bypass the On Death trait on the removed card.</div>

    <div>When a player goes second, they start with an extra Power-Up card in their hand, which if used gives them 1 extra energy for the remainder of the turn.</div>

  </div>
</template>

<script setup lang="ts">
import GameCard from '../components/game/GameCard.vue'
import type { CardInPlay } from '../types/game'

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
    @apply text-white rounded-full flex items-center justify-center border border-gray-900 z-20 shadow-lg w-8 h-8 bg-white relative -top-1;
}
</style>
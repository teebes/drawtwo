<template>
  <div class="design-reference min-h-screen bg-gray-50 dark:bg-gray-900">
    <div class="py-8">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <!-- Header -->
        <header class="mb-12 text-center">
          <h1 class="font-display text-4xl font-bold text-gray-900 dark:text-white lg:text-5xl">
            DrawTwo Design System
          </h1>
          <p class="mt-4 text-lg text-gray-600 dark:text-gray-300">
            Trading Card Game Design Reference & Style Guide
          </p>
        </header>

        <!-- Color Palette -->
        <Section title="Color Palette">
          <div class="grid gap-8 lg:grid-cols-2">
            <!-- Brand Colors -->
            <div>
              <h3 class="mb-4 text-xl font-semibold text-gray-900 dark:text-white">Brand Colors</h3>
              <div class="space-y-4">
                <ColorSwatch
                  label="Primary (Blue)"
                  :variations="[
                    { weight: '200', bgClass: 'bg-primary-200', textClass: 'text-gray-900' },
                    { weight: '400', bgClass: 'bg-primary-400', textClass: 'text-white' },
                    { weight: '600', bgClass: 'bg-primary-600', textClass: 'text-white' },
                    { weight: '800', bgClass: 'bg-primary-800', textClass: 'text-white' },
                    { weight: '900', bgClass: 'bg-primary-900', textClass: 'text-white' }
                  ]"
                />

                <ColorSwatch
                  label="Secondary (Purple)"
                  :variations="[
                    { weight: '200', bgClass: 'bg-secondary-200', textClass: 'text-gray-900' },
                    { weight: '400', bgClass: 'bg-secondary-400', textClass: 'text-white' },
                    { weight: '600', bgClass: 'bg-secondary-600', textClass: 'text-white' },
                    { weight: '800', bgClass: 'bg-secondary-800', textClass: 'text-white' },
                    { weight: '900', bgClass: 'bg-secondary-900', textClass: 'text-white' }
                  ]"
                />
              </div>
            </div>

            <!-- Card Rarity Colors -->
            <div>
              <h3 class="mb-4 text-xl font-semibold text-gray-900 dark:text-white">Card Rarity Colors</h3>
              <div class="grid grid-cols-2 gap-2">
                <ColorRarityItem name="Common" color-class="bg-card-common" />
                <ColorRarityItem name="Uncommon" color-class="bg-card-uncommon" />
                <ColorRarityItem name="Rare" color-class="bg-card-rare" />
                <ColorRarityItem name="Epic" color-class="bg-card-epic" />
                <ColorRarityItem name="Legendary" color-class="bg-card-legendary" />
                <ColorRarityItem name="Mythic" color-class="bg-card-mythic" />
              </div>
            </div>
          </div>
        </Section>

        <!-- Typography -->
        <Section title="Typography">
          <div class="grid gap-8 lg:grid-cols-3">
            <Panel title="Display Font (Cinzel)">
              <div class="space-y-2">
                <div class="font-display text-4xl font-bold text-gray-900 dark:text-white">DrawTwo</div>
                <div class="font-display text-2xl font-semibold text-gray-900 dark:text-white">Epic Quest</div>
                <div class="font-display text-xl text-gray-900 dark:text-white">Fire Dragon</div>
              </div>
            </Panel>

            <Panel title="Body Font (Inter)">
              <div class="space-y-2">
                <h1>Heading 1</h1>
                <h2>Heading 2</h2>
                <h3>Heading 3</h3>
                <div class="text-body">Body text for descriptions and card effects.</div>
                <div class="text-small">Small text for metadata.</div>

                <!--
                <div class="text-2xl font-bold text-gray-900 dark:text-white">Heading 1</div>
                <div class="text-xl font-semibold text-gray-900 dark:text-white">Heading 2</div>
                <div class="text-lg font-medium text-gray-900 dark:text-white">Heading 3</div>
                <div class="text-base text-gray-700 dark:text-gray-300">Body text for descriptions and card effects.</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Small text for metadata.</div>
                -->
              </div>
            </Panel>

            <Panel title="Monospace (JetBrains Mono)">
              <div class="space-y-2">
                <div class="font-mono text-lg text-gray-900 dark:text-white">Card ID: #001</div>
                <div class="font-mono text-base text-gray-700 dark:text-gray-300">Mana Cost: 3</div>
                <div class="font-mono text-sm text-gray-600 dark:text-gray-400">ATK: 4 / DEF: 5</div>
              </div>
            </Panel>
          </div>
        </Section>

        <Section title="Panels">
          <div class="grid gap-8 lg:grid-cols-3">
            <Panel title="Normal Panel" class="space-y-2">
              <div>This is a normal panel</div>
            </Panel>

            <Panel title="Error Panel" variant="error"class="space-y-2">
              <div>This is an error panel</div>
            </Panel>

            <Panel title="Success Panel" variant="success"class="space-y-2">
              <div>This is a success panel</div>
            </Panel>
          </div>
        </Section>

        <!-- Sample Trading Cards -->
        <Section title="Trading Cards">
          <div class="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            <TradingCard
              name="Lightning Bolt"
              :cost="1"
              icon="⚡"
              type="Instant Spell"
              text="Deal 3 damage to any target. The classic spell that started it all."
              card-type="spell"
            />

            <TradingCard
              name="Ancient Dragon"
              :cost="8"
              icon="🐉"
              type="Legendary Creature - Dragon"
              text="Flying, Trample. When Ancient Dragon enters the battlefield, deal 3 damage to all enemies."
              card-type="creature"
              :power="8"
              :toughness="8"
            />

            <TradingCard
              name="Mystic Armor"
              :cost="2"
              icon="🛡️"
              type="Epic Equipment"
              text="Equipped creature gets +2/+2 and hexproof. Equip cost: 1"
              card-type="equipment"
            />
          </div>
        </Section>

        <!-- Buttons & Interactive Elements -->
        <Section title="Interactive Elements">
          <div class="grid gap-8 lg:grid-cols-2">
            <Panel title="Buttons">
              <div class="space-y-4">
                <div class="flex flex-wrap gap-2">
                  <GameButton variant="primary">Primary</GameButton>
                  <GameButton variant="secondary">Secondary</GameButton>
                  <GameButton variant="danger">Danger</GameButton>
                </div>
                <div class="flex flex-wrap gap-2">
                  <GameButton variant="gradient" size="lg">Gradient CTA</GameButton>
                </div>
              </div>
            </Panel>

            <Panel title="Game Elements">
              <div class="space-y-4">
                <ManaDisplay
                  label="Mana Crystals"
                  :current-mana="3"
                  :total-crystals="5"
                  :animate="true"
                />

                <HealthBar
                  label="Health Bar"
                  :current="25"
                  :max="30"
                  color="red"
                />
              </div>
            </Panel>
          </div>
        </Section>

        <!-- Animations -->
        <Section title="Animations">
          <div class="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            <Panel title="Card Draw">
              <div class="flex justify-center">
                <div class="h-24 w-16 animate-card-draw rounded-lg bg-gradient-to-b from-blue-500 to-purple-600 shadow-lg"></div>
              </div>
            </Panel>

            <Panel title="Mana Pulse">
              <div class="flex justify-center">
                <div class="h-16 w-16 animate-mana-pulse rounded-full bg-blue-500 shadow-lg"></div>
              </div>
            </Panel>

            <Panel title="Card Glow">
              <div class="flex justify-center">
                <div class="card-glow h-24 w-16 rounded-lg bg-gradient-to-b from-yellow-400 to-orange-500"></div>
              </div>
            </Panel>
          </div>
        </Section>
      </div>
    </div>
  </div>
</template>

<script setup>
import Section from '../components/layout/Section.vue'
import Panel from '../components/layout/Panel.vue'
import ColorSwatch from '../components/design/ColorSwatch.vue'
import ColorRarityItem from '../components/design/ColorRarityItem.vue'
import TradingCard from '../components/game/TradingCard.vue'
import GameButton from '../components/ui/GameButton.vue'
import ManaDisplay from '../components/game/ManaDisplay.vue'
import HealthBar from '../components/game/HealthBar.vue'
</script>

<style scoped>
.design-reference {
  /* Custom styles if needed */
}
</style>
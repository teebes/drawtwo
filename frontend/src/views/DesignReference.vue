<template>
  <div class="design-reference min-h-screen bg-gray-50 dark:bg-gray-900">
    <AppHeader />

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
        <section class="mb-16">
          <h2 class="mb-8 font-display text-3xl font-bold text-gray-900 dark:text-white">Color Palette</h2>

          <div class="grid gap-8 lg:grid-cols-2">
            <!-- Brand Colors -->
            <div>
              <h3 class="mb-4 text-xl font-semibold text-gray-900 dark:text-white">Brand Colors</h3>
              <div class="space-y-4">
                <div class="rounded-lg border border-gray-200 dark:border-gray-700">
                  <div class="grid grid-cols-5">
                    <div class="h-16 bg-primary-200 flex items-center justify-center text-xs font-mono">200</div>
                    <div class="h-16 bg-primary-400 flex items-center justify-center text-xs font-mono text-white">400</div>
                    <div class="h-16 bg-primary-600 flex items-center justify-center text-xs font-mono text-white">600</div>
                    <div class="h-16 bg-primary-800 flex items-center justify-center text-xs font-mono text-white">800</div>
                    <div class="h-16 bg-primary-900 flex items-center justify-center text-xs font-mono text-white">900</div>
                  </div>
                  <div class="p-2 text-sm font-medium text-gray-700 dark:text-gray-300">Primary (Blue)</div>
                </div>

                <div class="rounded-lg border border-gray-200 dark:border-gray-700">
                  <div class="grid grid-cols-5">
                    <div class="h-16 bg-secondary-200 flex items-center justify-center text-xs font-mono">200</div>
                    <div class="h-16 bg-secondary-400 flex items-center justify-center text-xs font-mono text-white">400</div>
                    <div class="h-16 bg-secondary-600 flex items-center justify-center text-xs font-mono text-white">600</div>
                    <div class="h-16 bg-secondary-800 flex items-center justify-center text-xs font-mono text-white">800</div>
                    <div class="h-16 bg-secondary-900 flex items-center justify-center text-xs font-mono text-white">900</div>
                  </div>
                  <div class="p-2 text-sm font-medium text-gray-700 dark:text-gray-300">Secondary (Purple)</div>
                </div>
              </div>
            </div>

            <!-- Card Rarity Colors -->
            <div>
              <h3 class="mb-4 text-xl font-semibold text-gray-900 dark:text-white">Card Rarity Colors</h3>
              <div class="grid grid-cols-2 gap-2">
                <div class="flex items-center space-x-3 rounded-lg bg-gray-100 p-3 dark:bg-gray-800">
                  <div class="h-6 w-6 rounded-full bg-card-common"></div>
                  <span class="text-sm font-medium text-gray-900 dark:text-white">Common</span>
                </div>
                <div class="flex items-center space-x-3 rounded-lg bg-gray-100 p-3 dark:bg-gray-800">
                  <div class="h-6 w-6 rounded-full bg-card-uncommon"></div>
                  <span class="text-sm font-medium text-gray-900 dark:text-white">Uncommon</span>
                </div>
                <div class="flex items-center space-x-3 rounded-lg bg-gray-100 p-3 dark:bg-gray-800">
                  <div class="h-6 w-6 rounded-full bg-card-rare"></div>
                  <span class="text-sm font-medium text-gray-900 dark:text-white">Rare</span>
                </div>
                <div class="flex items-center space-x-3 rounded-lg bg-gray-100 p-3 dark:bg-gray-800">
                  <div class="h-6 w-6 rounded-full bg-card-epic"></div>
                  <span class="text-sm font-medium text-gray-900 dark:text-white">Epic</span>
                </div>
                <div class="flex items-center space-x-3 rounded-lg bg-gray-100 p-3 dark:bg-gray-800">
                  <div class="h-6 w-6 rounded-full bg-card-legendary"></div>
                  <span class="text-sm font-medium text-gray-900 dark:text-white">Legendary</span>
                </div>
                <div class="flex items-center space-x-3 rounded-lg bg-gray-100 p-3 dark:bg-gray-800">
                  <div class="h-6 w-6 rounded-full bg-card-mythic"></div>
                  <span class="text-sm font-medium text-gray-900 dark:text-white">Mythic</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Typography -->
        <section class="mb-16">
          <h2 class="mb-8 font-display text-3xl font-bold text-gray-900 dark:text-white">Typography</h2>

          <div class="grid gap-8 lg:grid-cols-3">
            <div class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800">
              <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Display Font (Cinzel)</h3>
              <div class="space-y-2">
                <div class="font-display text-4xl font-bold text-gray-900 dark:text-white">DrawTwo</div>
                <div class="font-display text-2xl font-semibold text-gray-900 dark:text-white">Epic Quest</div>
                <div class="font-display text-xl text-gray-900 dark:text-white">Fire Dragon</div>
              </div>
            </div>

            <div class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800">
              <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Body Font (Inter)</h3>
              <div class="space-y-2">
                <div class="text-2xl font-bold text-gray-900 dark:text-white">Heading 1</div>
                <div class="text-xl font-semibold text-gray-900 dark:text-white">Heading 2</div>
                <div class="text-lg font-medium text-gray-900 dark:text-white">Heading 3</div>
                <div class="text-base text-gray-700 dark:text-gray-300">Body text for descriptions and card effects.</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Small text for metadata.</div>
              </div>
            </div>

            <div class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800">
              <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Monospace (JetBrains Mono)</h3>
              <div class="space-y-2">
                <div class="font-mono text-lg text-gray-900 dark:text-white">Card ID: #001</div>
                <div class="font-mono text-base text-gray-700 dark:text-gray-300">Mana Cost: 3</div>
                <div class="font-mono text-sm text-gray-600 dark:text-gray-400">ATK: 4 / DEF: 5</div>
              </div>
            </div>
          </div>
        </section>

        <!-- Sample Trading Cards -->
        <section class="mb-16">
          <h2 class="mb-8 font-display text-3xl font-bold text-gray-900 dark:text-white">Trading Cards</h2>

          <div class="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            <!-- Spell Card -->
            <div class="group transform transition-all duration-300 hover:-translate-y-2 hover:shadow-xl">
              <div class="h-96 w-64 overflow-hidden rounded-xl border-2 border-blue-500 bg-gradient-to-b from-blue-50 to-blue-100 p-1 dark:from-blue-900/50 dark:to-blue-800/50">
                <div class="flex h-full flex-col rounded-lg bg-white p-4 dark:bg-gray-900">
                  <div class="flex items-center justify-between">
                    <h4 class="font-display text-lg font-bold text-gray-900 dark:text-white">Lightning Bolt</h4>
                    <div class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 text-sm font-bold text-white">1</div>
                  </div>

                  <div class="my-4 flex flex-1 items-center justify-center rounded bg-gradient-to-br from-yellow-200 to-blue-300 text-6xl">⚡</div>

                  <div class="text-sm text-gray-600 dark:text-gray-400 mb-2">Instant Spell</div>

                  <div class="text-sm text-gray-800 dark:text-gray-200">
                    Deal 3 damage to any target. The classic spell that started it all.
                  </div>
                </div>
              </div>
            </div>

            <!-- Creature Card -->
            <div class="group transform transition-all duration-300 hover:-translate-y-2 hover:shadow-xl">
              <div class="h-96 w-64 overflow-hidden rounded-xl border-2 border-yellow-500 bg-gradient-to-b from-yellow-50 to-yellow-100 p-1 dark:from-yellow-900/50 dark:to-yellow-800/50">
                <div class="flex h-full flex-col rounded-lg bg-white p-4 dark:bg-gray-900">
                  <div class="flex items-center justify-between">
                    <h4 class="font-display text-lg font-bold text-gray-900 dark:text-white">Ancient Dragon</h4>
                    <div class="flex h-8 w-8 items-center justify-center rounded-full bg-red-500 text-sm font-bold text-white">8</div>
                  </div>

                  <div class="my-4 flex flex-1 items-center justify-center rounded bg-gradient-to-br from-red-200 to-orange-300 text-6xl">🐉</div>

                  <div class="text-sm text-gray-600 dark:text-gray-400 mb-2">Legendary Creature - Dragon</div>

                  <div class="text-sm text-gray-800 dark:text-gray-200 flex-1">
                    Flying, Trample. When Ancient Dragon enters the battlefield, deal 3 damage to all enemies.
                  </div>

                  <div class="flex justify-end mt-2">
                    <div class="rounded bg-gray-200 px-3 py-1 text-sm font-bold text-gray-800 dark:bg-gray-700 dark:text-gray-200">8/8</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Equipment Card -->
            <div class="group transform transition-all duration-300 hover:-translate-y-2 hover:shadow-xl">
              <div class="h-96 w-64 overflow-hidden rounded-xl border-2 border-purple-500 bg-gradient-to-b from-purple-50 to-purple-100 p-1 dark:from-purple-900/50 dark:to-purple-800/50">
                <div class="flex h-full flex-col rounded-lg bg-white p-4 dark:bg-gray-900">
                  <div class="flex items-center justify-between">
                    <h4 class="font-display text-lg font-bold text-gray-900 dark:text-white">Mystic Armor</h4>
                    <div class="flex h-8 w-8 items-center justify-center rounded-full bg-purple-500 text-sm font-bold text-white">2</div>
                  </div>

                  <div class="my-4 flex flex-1 items-center justify-center rounded bg-gradient-to-br from-gray-200 to-purple-300 text-6xl">🛡️</div>

                  <div class="text-sm text-gray-600 dark:text-gray-400 mb-2">Epic Equipment</div>

                  <div class="text-sm text-gray-800 dark:text-gray-200">
                    Equipped creature gets +2/+2 and hexproof. Equip cost: 1
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Buttons & Interactive Elements -->
        <section class="mb-16">
          <h2 class="mb-8 font-display text-3xl font-bold text-gray-900 dark:text-white">Interactive Elements</h2>

          <div class="grid gap-8 lg:grid-cols-2">
            <div class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800">
              <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Buttons</h3>
              <div class="space-y-4">
                <div class="flex flex-wrap gap-2">
                  <button class="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors">Primary</button>
                  <button class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 transition-colors">Secondary</button>
                  <button class="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors">Danger</button>
                </div>
                <div class="flex flex-wrap gap-2">
                  <button class="rounded-xl bg-gradient-to-r from-primary-600 to-secondary-600 px-6 py-3 text-base font-medium text-white shadow-lg hover:from-primary-700 hover:to-secondary-700 transition-all">Gradient CTA</button>
                </div>
              </div>
            </div>

            <div class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800">
              <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Game Elements</h3>
              <div class="space-y-4">
                <!-- Mana crystals -->
                <div>
                  <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">Mana Crystals</p>
                  <div class="flex space-x-1">
                    <div class="h-6 w-6 rounded-full bg-blue-500 animate-mana-pulse"></div>
                    <div class="h-6 w-6 rounded-full bg-blue-500"></div>
                    <div class="h-6 w-6 rounded-full bg-blue-500"></div>
                    <div class="h-6 w-6 rounded-full bg-gray-300"></div>
                    <div class="h-6 w-6 rounded-full bg-gray-300"></div>
                  </div>
                </div>

                <!-- Health bar -->
                <div>
                  <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">Health Bar</p>
                  <div class="flex items-center space-x-2">
                    <div class="h-3 w-32 rounded-full bg-gray-300">
                      <div class="h-3 w-3/4 rounded-full bg-red-500"></div>
                    </div>
                    <span class="font-mono text-sm text-gray-900 dark:text-white">25/30</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Animations -->
        <section class="mb-16">
          <h2 class="mb-8 font-display text-3xl font-bold text-gray-900 dark:text-white">Animations</h2>

          <div class="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            <div class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800">
              <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Card Draw</h3>
              <div class="flex justify-center">
                <div class="h-24 w-16 animate-card-draw rounded-lg bg-gradient-to-b from-blue-500 to-purple-600 shadow-lg"></div>
              </div>
            </div>

            <div class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800">
              <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Mana Pulse</h3>
              <div class="flex justify-center">
                <div class="h-16 w-16 animate-mana-pulse rounded-full bg-blue-500 shadow-lg"></div>
              </div>
            </div>

            <div class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800">
              <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Card Glow</h3>
              <div class="flex justify-center">
                <div class="card-glow h-24 w-16 rounded-lg bg-gradient-to-b from-yellow-400 to-orange-500"></div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import AppHeader from '../components/AppHeader.vue'
</script>

<style scoped>
.design-reference {
  /* Custom styles if needed */
}
</style>
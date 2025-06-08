<template>
  <div class="lobby">
    <AppHeader />

    <main class="flex-1">
      <!-- Welcome Section -->
      <section class="bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="text-center">
            <h1 class="font-display text-4xl font-bold text-white sm:text-5xl">
              Welcome to the Lobby
            </h1>
            <p class="mt-4 text-xl text-primary-100">
              Ready to duel? Choose your game mode and find opponents.
            </p>
          </div>
        </div>
      </section>

      <!-- Game Modes -->
      <section class="py-16 bg-gray-50 dark:bg-gray-800">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="text-center font-display text-3xl font-bold text-gray-900 dark:text-white mb-12">
            Choose Your Battle
          </h2>

          <div class="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            <!-- Quick Match -->
            <div class="group cursor-pointer rounded-2xl bg-white p-8 shadow-sm transition-all hover:shadow-xl hover:-translate-y-1 dark:bg-gray-900">
              <div class="text-center">
                <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-r from-green-500 to-emerald-600">
                  <span class="text-2xl">⚡</span>
                </div>
                <h3 class="font-display text-xl font-bold text-gray-900 dark:text-white">Quick Match</h3>
                <p class="mt-2 text-gray-600 dark:text-gray-300">
                  Jump into a fast-paced match with players of similar skill level.
                </p>
                <button class="mt-6 w-full rounded-lg bg-green-600 px-4 py-2 font-medium text-white transition-colors hover:bg-green-700">
                  Find Match
                </button>
              </div>
            </div>

            <!-- Ranked Play -->
            <div class="group cursor-pointer rounded-2xl bg-white p-8 shadow-sm transition-all hover:shadow-xl hover:-translate-y-1 dark:bg-gray-900">
              <div class="text-center">
                <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-r from-purple-500 to-violet-600">
                  <span class="text-2xl">👑</span>
                </div>
                <h3 class="font-display text-xl font-bold text-gray-900 dark:text-white">Ranked Play</h3>
                <p class="mt-2 text-gray-600 dark:text-gray-300">
                  Climb the ladder and prove your mastery in competitive matches.
                </p>
                <button class="mt-6 w-full rounded-lg bg-purple-600 px-4 py-2 font-medium text-white transition-colors hover:bg-purple-700">
                  Enter Ranked
                </button>
              </div>
            </div>

            <!-- Practice Mode -->
            <div class="group cursor-pointer rounded-2xl bg-white p-8 shadow-sm transition-all hover:shadow-xl hover:-translate-y-1 dark:bg-gray-900">
              <div class="text-center">
                <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-r from-blue-500 to-cyan-600">
                  <span class="text-2xl">🎯</span>
                </div>
                <h3 class="font-display text-xl font-bold text-gray-900 dark:text-white">Practice Mode</h3>
                <p class="mt-2 text-gray-600 dark:text-gray-300">
                  Hone your skills against AI opponents or practice deck strategies.
                </p>
                <button class="mt-6 w-full rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-700">
                  Start Practice
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Player Stats -->
      <section class="py-16">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="rounded-2xl bg-white p-8 shadow-sm dark:bg-gray-900">
            <h2 class="font-display text-2xl font-bold text-gray-900 dark:text-white mb-8">Your Stats</h2>

            <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              <div class="text-center">
                <div class="text-3xl font-bold text-primary-600 dark:text-primary-400">Bronze III</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Current Rank</div>
              </div>
              <div class="text-center">
                <div class="text-3xl font-bold text-green-600">24</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Wins This Season</div>
              </div>
              <div class="text-center">
                <div class="text-3xl font-bold text-red-600">18</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Losses This Season</div>
              </div>
              <div class="text-center">
                <div class="text-3xl font-bold text-purple-600">3</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Decks Created</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Recent Activity -->
      <section class="border-t border-gray-200 bg-gray-50 py-16 dark:border-gray-700 dark:bg-gray-800">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="font-display text-2xl font-bold text-gray-900 dark:text-white mb-8">Recent Matches</h2>

          <div class="space-y-4">
            <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-900">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                  <div class="flex h-8 w-8 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
                    <span class="text-sm font-bold text-green-800 dark:text-green-200">W</span>
                  </div>
                  <div>
                    <div class="font-medium text-gray-900 dark:text-white">Victory vs. DragonMaster</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">Ranked Match • 2 hours ago</div>
                  </div>
                </div>
                <div class="text-sm text-gray-600 dark:text-gray-400">+25 MMR</div>
              </div>
            </div>

            <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-900">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                  <div class="flex h-8 w-8 items-center justify-center rounded-full bg-red-100 dark:bg-red-900">
                    <span class="text-sm font-bold text-red-800 dark:text-red-200">L</span>
                  </div>
                  <div>
                    <div class="font-medium text-gray-900 dark:text-white">Defeat vs. SpellCaster99</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">Ranked Match • 5 hours ago</div>
                  </div>
                </div>
                <div class="text-sm text-gray-600 dark:text-gray-400">-18 MMR</div>
              </div>
            </div>

            <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-900">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                  <div class="flex h-8 w-8 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
                    <span class="text-sm font-bold text-green-800 dark:text-green-200">W</span>
                  </div>
                  <div>
                    <div class="font-medium text-gray-900 dark:text-white">Victory vs. CardShark</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">Quick Match • 1 day ago</div>
                  </div>
                </div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Casual</div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import AppHeader from '../components/AppHeader.vue'
</script>

<style scoped>
.lobby {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
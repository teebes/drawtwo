<template>
  <div class="home">
    <main>
      <!-- Hero Section -->
      <section class="relative min-h-[85vh] flex items-center justify-center px-6 py-24 sm:px-8 lg:px-12">
        <div class="mx-auto max-w-3xl text-center">
          <h1 class="font-display text-5xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-6xl lg:text-7xl">
            Draw Two
          </h1>
          <p class="mt-8 text-xl leading-relaxed text-gray-600 dark:text-gray-400 sm:text-2xl">
            An open-source engine for building online trading card games.
          </p>

          <div class="mt-16">
            <button
              class="inline-flex items-center justify-center rounded-xl bg-gray-900 px-12 py-5 text-lg font-medium text-white shadow-lg transition-all hover:bg-gray-800 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-4 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100 dark:focus:ring-white sm:text-xl"
            >
              Play
            </button>
          </div>
        </div>
      </section>

      <!-- About Section -->
      <section class="border-t border-gray-200 bg-gray-50 px-6 py-24 dark:border-gray-800 dark:bg-gray-900/50 sm:px-8 lg:px-12">
        <div class="mx-auto max-w-2xl">
          <h2 class="font-display text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl">
            What is Draw Two?
          </h2>

          <div class="mt-8 space-y-6 text-lg leading-relaxed text-gray-700 dark:text-gray-300">
            <p>
              Draw Two is a game engine designed for building online trading card games.
              Think Hearthstone or Magic: The Gathering Online, but open source and extensible.
            </p>

            <p>
              The first playable title built on Draw Two is <span class="font-semibold text-gray-900 dark:text-white">Archetype</span>,
              a strategic card game where every decision matters.
            </p>

            <p>
              The engine is built with modern web technologies and designed to support
              multiple game titles, each with their own unique cards, mechanics, and gameplay.
            </p>
          </div>

          <div class="mt-12 flex items-center gap-3">
            <svg class="h-6 w-6 text-gray-700 dark:text-gray-300" fill="currentColor" viewBox="0 0 24 24">
              <path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd"></path>
            </svg>
            <a
              href="https://github.com/teebes/drawtwo"
              target="_blank"
              rel="noopener noreferrer"
              class="text-lg font-semibold text-gray-900 underline decoration-2 underline-offset-4 transition-colors hover:text-gray-700 dark:text-white dark:hover:text-gray-300"
            >
              View on GitHub
            </a>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
</script>

<style scoped>
.home {
  min-height: 100vh;
}
</style>
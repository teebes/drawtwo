<template>
  <div class="home">
    <main>
      <!-- Hero Section -->
      <section class="relative min-h-[85vh] flex items-center justify-center px-6 py-24 sm:px-8 lg:px-12">
        <div class="hero-logo" aria-hidden="true">
          <img src="/drawtwo_logo.png" alt="" />
        </div>
        <div class="mx-auto max-w-3xl text-center relative z-10">
          <h1 class="font-display text-5xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-6xl lg:text-7xl">
            Draw Two
          </h1>
          <p class="mt-8 text-xl leading-relaxed text-gray-600 dark:text-gray-400 sm:text-2xl">
            An open-source engine for building strategy card games.
          </p>

          <div class="mt-16">
            <button
              @click="handlePlayClick"
              class="inline-flex items-center justify-center rounded-xl bg-primary-600 px-12 py-5 text-lg font-medium text-white shadow-lg transition-all hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-seon-900 focus:ring-offset-4"
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
              Draw Two is a game engine designed for building strategy card games, open source and extensible.
            </p>

            <p>
              The first playable title built on Draw Two is
              <router-link
                to="/archetype"
                class="font-semibold text-gray-900 underline decoration-2 underline-offset-2 transition-colors hover:text-gray-700 dark:text-white dark:hover:text-gray-300"
              >
                Archetype
              </router-link>,
              a prototypical trading card game that serves as both a full game in its own right
              and a template for builders to create other games.
            </p>

          </div>

          <div class="mt-12 flex items-center gap-3">
            <a
              href="https://github.com/teebes/drawtwo"
              target="_blank"
              rel="noopener noreferrer"
              class="text-lg font-semibold text-gray-900 underline decoration-2 underline-offset-4 transition-colors hover:text-gray-700 dark:text-white dark:hover:text-gray-300"
            >
              View on GitHub
            </a>
          </div>

          <div class="mt-12 flex items-center gap-3">
            <a href="https://x.com/thibaudm" target="_blank" rel="noopener noreferrer" class="text-lg font-semibold text-gray-900 underline decoration-2 underline-offset-4 transition-colors hover:text-gray-700 dark:text-white dark:hover:text-gray-300">
              Follow on X
            </a>

          </div>
        </div>
      </section>

      <!-- Footer -->
      <footer class="border-t border-gray-200 bg-white px-6 py-12 dark:border-gray-800 dark:bg-gray-950 sm:px-8 lg:px-12">
        <div class="mx-auto max-w-2xl">
          <div class="flex flex-col items-center justify-center gap-6 sm:flex-row sm:gap-8">
            <router-link
              to="/privacy"
              class="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
            >
              Privacy Policy
            </router-link>
            <span class="hidden text-gray-300 dark:text-gray-700 sm:inline">|</span>
            <router-link
              to="/terms"
              class="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
            >
              Terms of Service
            </router-link>
          </div>
          <div class="mt-6 text-center">
            <p class="text-sm text-gray-500 dark:text-gray-500">
              &copy; {{ currentYear }} Morel Software, LLC. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import { computed } from 'vue'

const authStore = useAuthStore()
const router = useRouter()

const currentYear = computed(() => new Date().getFullYear())

const handlePlayClick = () => {
  if (authStore.isAuthenticated) {
    router.push({ name: 'Play' })
  } else {
    router.push({ name: 'Login' })
  }
}
</script>

<style scoped>
.home {
  min-height: 100vh;
}

.hero-logo {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  transform: translateY(-100px);
}

.hero-logo img {
  width: min(60vw, 420px);
  opacity: 0.1;
  filter: drop-shadow(0 0 40px rgba(0, 0, 0, 0.35));
}
</style>
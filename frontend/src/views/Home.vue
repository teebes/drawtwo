<template>
  <div class="home">
    <main>
      <!-- Hero Section -->
      <section class="relative flex min-h-[90vh] items-center justify-center px-6 py-24 sm:px-8 lg:px-12">
        <div class="hero-logo" aria-hidden="true">
          <img src="/drawtwo_logo.png" alt="" />
        </div>
        <div class="relative z-10 mx-auto max-w-3xl text-center">
          <h1 class="font-display text-5xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-6xl lg:text-7xl">
            Draw Two
          </h1>
          <p class="mt-8 text-xl leading-relaxed text-gray-600 dark:text-gray-400 sm:text-2xl">
            An open-source engine for building strategy card games.
          </p>

          <div class="mt-16">
            <button
              @click="handlePlayClick"
              :disabled="startingIntro"
              class="inline-flex items-center justify-center rounded-xl bg-primary-600 px-14 py-5 text-lg font-medium text-white shadow-lg transition-all hover:bg-primary-700 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-4 dark:focus:ring-offset-gray-950"
            >
              {{ startingIntro ? 'Loading...' : 'Play' }}
            </button>
            <p v-if="playError" class="mt-4 text-sm text-red-600 dark:text-red-400">
              {{ playError }}
            </p>
          </div>
        </div>
      </section>

      <!-- iOS App Section -->
      <section class="border-t border-gray-200 bg-gray-50 px-6 py-20 dark:border-gray-800 dark:bg-gray-900/50 sm:px-8 lg:px-12">
        <div class="mx-auto max-w-2xl text-center">
          <h2 class="font-display text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl">
            Play on iPhone
          </h2>
          <p class="mt-6 text-lg leading-relaxed text-gray-700 dark:text-gray-300">
            Archetype, the first title built on Draw Two, is available on the App&nbsp;Store.
          </p>
          <a
            href="https://apps.apple.com/us/app/archetype-draw-two/id6785131475"
            target="_blank"
            rel="noopener noreferrer"
            class="mt-10 inline-block transition-opacity hover:opacity-80"
          >
            <img
              src="https://tools.applemediaservices.com/api/badges/download-on-the-app-store/black/en-us"
              alt="Download on the App Store"
              class="h-14 dark:hidden"
            />
            <img
              src="https://tools.applemediaservices.com/api/badges/download-on-the-app-store/white/en-us"
              alt="Download on the App Store"
              class="hidden h-14 dark:block"
            />
          </a>
        </div>
      </section>

      <!-- How to Play Section -->
      <section class="border-t border-gray-200 bg-white px-6 py-20 dark:border-gray-800 dark:bg-gray-950 sm:px-8 lg:px-12">
        <div class="mx-auto max-w-2xl text-center">
          <h2 class="font-display text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl">
            How to Play
          </h2>
        </div>
        <TitleHelp :show-title="false" class="!py-4 mt-4" />
      </section>

      <!-- About Section -->
      <section class="border-t border-gray-200 bg-gray-50 px-6 py-20 dark:border-gray-800 dark:bg-gray-900/50 sm:px-8 lg:px-12">
        <div class="mx-auto max-w-2xl">
          <h2 class="font-display text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl">
            What is Draw Two?
          </h2>

          <div class="mt-8 space-y-6 text-lg leading-relaxed text-gray-700 dark:text-gray-300">
            <p>
              Draw Two is a game engine designed for building strategy card games, open source and extensible.
            </p>

            <p>
              <router-link
                to="/archetype"
                class="font-semibold text-gray-900 underline decoration-2 underline-offset-2 transition-colors hover:text-gray-700 dark:text-white dark:hover:text-gray-300"
              >
                Archetype
              </router-link>
              is the first playable title built on the engine and showcases what it can do.
              Want to build your own game? Clone the repo and make it yours.
            </p>
          </div>

          <div class="mt-12 flex flex-wrap items-center gap-8">
            <a
              href="https://github.com/teebes/drawtwo"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-2 text-lg font-semibold text-gray-900 underline decoration-2 underline-offset-4 transition-colors hover:text-gray-700 dark:text-white dark:hover:text-gray-300"
            >
              <svg class="h-6 w-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0 0 22 12.017C22 6.484 17.522 2 12 2Z" />
              </svg>
              View on GitHub
            </a>

            <a
              href="https://x.com/thibaudm"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-2 text-lg font-semibold text-gray-900 underline decoration-2 underline-offset-4 transition-colors hover:text-gray-700 dark:text-white dark:hover:text-gray-300"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.45-6.231Zm-1.161 17.52h1.833L7.084 4.126H5.117l11.966 15.644Z" />
              </svg>
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

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { computed, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { startIntroScenario } from '../services/introScenario'
import TitleHelp from '../components/title/TitleHelp.vue'

const router = useRouter()
const authStore = useAuthStore()
const startingIntro = ref(false)
const playError = ref('')

const currentYear = computed(() => new Date().getFullYear())

const handlePlayClick = async () => {
  if (startingIntro.value) {
    return
  }

  if (authStore.isAuthenticated) {
    playError.value = ''
    router.push({ name: 'Play' })
    return
  }

  startingIntro.value = true
  playError.value = ''

  try {
    const game = await startIntroScenario()
    router.push({
      name: 'Board',
      params: {
        slug: game.title_slug,
        game_id: game.id,
      },
      query: {
        intro: '1',
      },
    })
  } catch (error) {
    console.error('Failed to start intro game:', error)
    playError.value = 'Unable to start the intro game. Please try again.'
  } finally {
    startingIntro.value = false
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

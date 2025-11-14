<template>
  <header class="border-b border-gray-200 bg-white/80 backdrop-blur-sm dark:border-gray-700 dark:bg-gray-900/80">
    <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div class="flex h-16 items-center justify-between">
        <div class="flex items-center">
          <router-link :to="authStore.isAuthenticated ? '/play' : '/'" class="flex items-center">
            <img
              src="/drawtwo_logo.png"
              alt="DrawTwo Logo"
              class="sm:mr-2 h-8 w-8 rounded-lg object-contain relative bottom-[2px]"
            />
            <h1 class="font-display text-2xl font-bold text-gray-900 dark:text-white hidden sm:block">
              DrawTwo
            </h1>
          </router-link>
          <!-- Show title name when viewing a title -->
          <div v-if="titleStore.isViewingTitle" class="flex items-center">
            <span class="text-gray-400 dark:text-gray-500 mx-2">/</span>
            <router-link
              :to="{ name: 'Title', params: { slug: titleStore.titleSlug } }"
              class="font-display text-xl font-semibold text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors"
            >
              {{ titleStore.titleName }}
            </router-link>
          </div>
        </div>

        <nav class="flex items-center space-x-4">
          <div v-if="authStore.isAuthenticated" class="relative" ref="profileMenuRef" @keydown.esc="closeProfileMenu">
            <button
              type="button"
              class="relative inline-flex h-11 w-11 items-center justify-center rounded-full bg-gray-900 text-white shadow-sm transition-all hover:scale-105 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:bg-gray-800 dark:text-gray-100 dark:focus:ring-offset-gray-900"
              @click="toggleProfileMenu"
              aria-haspopup="menu"
              :aria-expanded="isProfileMenuOpen"
            >
              <span class="sr-only">Open profile menu</span>
              <img
                v-if="profileImage"
                :src="profileImage"
                alt="Profile avatar"
                class="h-full w-full rounded-full object-cover"
              />
              <span v-else class="text-base font-semibold">
                {{ profileInitial }}
              </span>
            </button>

            <transition
              enter-active-class="transition ease-out duration-150"
              enter-from-class="opacity-0 translate-y-1"
              enter-to-class="opacity-100 translate-y-0"
              leave-active-class="transition ease-in duration-100"
              leave-from-class="opacity-100 translate-y-0"
              leave-to-class="opacity-0 translate-y-1"
            >
              <div
                v-if="isProfileMenuOpen"
                class="absolute right-0 z-50 mt-3 w-64 rounded-2xl border border-gray-200 bg-white p-2 shadow-xl ring-1 ring-black/5 dark:border-gray-700 dark:bg-gray-900"
                role="menu"
                aria-label="Profile menu"
              >
                <div class="px-4 py-3">
                  <p class="text-sm text-gray-500 dark:text-gray-400">Signed in as</p>
                  <p class="text-sm font-semibold text-gray-900 dark:text-white truncate">
                    {{ authStore.user?.username || authStore.user?.email }}
                  </p>
                </div>
                <div class="space-y-1">
                  <button
                    type="button"
                    class="flex w-full items-center rounded-xl px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
                    @click="() => goToRoute('/profile')"
                    role="menuitem"
                  >
                    Profile
                  </button>
                  <button
                    type="button"
                    class="flex w-full items-center rounded-xl px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
                    @click="() => goToRoute('/friends')"
                    role="menuitem"
                  >
                    Friends
                  </button>
                </div>
                <div class="my-2 rounded-xl bg-gray-50 px-4 py-3 dark:bg-gray-800">
                  <div class="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-200">
                    <span>Light / Dark</span>
                    <ThemeToggle />
                  </div>
                </div>
                <div class="border-t border-gray-100 pt-2 dark:border-gray-800">
                  <button
                    type="button"
                    class="flex w-full items-center rounded-xl px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/30"
                    @click="handleSignOut"
                    role="menuitem"
                  >
                    Sign Out
                  </button>
                </div>
              </div>
            </transition>
          </div>

          <div v-else>
            <router-link
              to="/login"
              class="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-all hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
            >
              Login / Sign Up
            </router-link>
          </div>
        </nav>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import ThemeToggle from './ui/ThemeToggle.vue'
import { useAuthStore } from '../stores/auth'
import { useTitleStore } from '../stores/title'

const authStore = useAuthStore()
const titleStore = useTitleStore()
const router = useRouter()

const isProfileMenuOpen = ref(false)
const profileMenuRef = ref<HTMLElement | null>(null)

const profileImage = computed(() => authStore.user?.avatar ?? '')
const profileInitial = computed(() => {
  if (authStore.user?.username) {
    return authStore.user.username.charAt(0).toUpperCase()
  }
  if (authStore.user?.email) {
    return authStore.user.email.charAt(0).toUpperCase()
  }
  return 'P'
})

const toggleProfileMenu = () => {
  isProfileMenuOpen.value = !isProfileMenuOpen.value
}

const closeProfileMenu = () => {
  if (isProfileMenuOpen.value) {
    isProfileMenuOpen.value = false
  }
}

const goToRoute = (path: string) => {
  router.push(path)
  closeProfileMenu()
}

const handleSignOut = async () => {
  await authStore.logout()
  closeProfileMenu()
  router.push('/')
}

onClickOutside(profileMenuRef, () => {
  closeProfileMenu()
})
</script>
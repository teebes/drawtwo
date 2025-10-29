<template>
  <header class="fixed top-0 left-0 right-0 z-50 border-b border-gray-200 bg-white/80 backdrop-blur-sm dark:border-gray-700 dark:bg-gray-900/80">
    <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div class="flex h-16 items-center justify-between">
        <div class="flex items-center">
          <router-link to="/" class="flex items-center">
            <h1 class="font-display text-2xl font-bold text-gray-900 dark:text-white hidden sm:block">
              DrawTwo
            </h1>
            <img
              src="/drawtwo_logo.png"
              alt="DrawTwo Logo"
              class="ml-2 h-8 w-8 rounded-lg object-contain"
            />
          </router-link>
          <!-- Show title name when viewing a title -->
          <div v-if="titleStore.isViewingTitle" class="ml-4 flex items-center">
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
          <!-- Show different navigation based on authentication status -->
          <div v-if="authStore.isAuthenticated" class="flex items-center space-x-4">
            <router-link
              to="/lobby"
              class="text-sm font-medium text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
            >
              Lobby
            </router-link>
            <router-link
              to="/friends"
              class="text-sm font-medium text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
            >
              Friends
            </router-link>
            <router-link
              to="/profile"
              class="inline-flex items-center rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-all hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 dark:focus:ring-offset-gray-900"
            >
              Profile
            </router-link>
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

<script setup>
import { useAuthStore } from '../stores/auth'
import { useTitleStore } from '../stores/title'

const authStore = useAuthStore()
const titleStore = useTitleStore()
</script>
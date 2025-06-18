<template>
  <button
    @click="themeStore.toggleTheme"
    class="relative inline-flex h-10 w-10 items-center justify-center rounded-lg border border-gray-200 bg-white text-gray-900 transition-all hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700"
    :title="themeStore.isDark ? 'Switch to light mode' : 'Switch to dark mode'"
  >
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="scale-0 rotate-90 opacity-0"
      enter-to-class="scale-100 rotate-0 opacity-100"
      leave-active-class="transition-all duration-300 ease-out"
      leave-from-class="scale-100 rotate-0 opacity-100"
      leave-to-class="scale-0 -rotate-90 opacity-0"
    >
      <Sun v-if="themeStore.isDark" :size="18" class="text-yellow-500" />
      <Moon v-else :size="18" class="text-slate-700 dark:text-slate-300" />
    </Transition>
  </button>
</template>

<script setup>
import { Sun, Moon } from 'lucide-vue-next'
import { useThemeStore } from '../../stores/theme.js'

const themeStore = useThemeStore()
</script>
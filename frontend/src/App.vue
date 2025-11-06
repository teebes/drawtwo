<template>
  <div id="app" class="h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300 flex flex-col overflow-hidden">
    <AppHeader v-if="!shouldHideHeader" />
    <div :class="{ 'pt-16': !shouldHideHeader }" class="flex-1 overflow-y-auto">
      <router-view />
    </div>
    <ToastNotifications />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useThemeStore } from './stores/theme'
import AppHeader from './components/AppHeader.vue'
import ToastNotifications from './components/ui/ToastNotifications.vue'

const route = useRoute()
const themeStore = useThemeStore()

const shouldHideHeader = computed(() => {
  return route.meta?.hideHeader === true
})

onMounted(() => {
  themeStore.initTheme()
})
</script>

<style>
/* Import Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Cinzel:wght@400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600&display=swap');

#app {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Custom scrollbar for dark mode */
* {
  scrollbar-width: thin;
  scrollbar-color: rgb(75 85 99) rgb(31 41 55);
}

*::-webkit-scrollbar {
  width: 8px;
}

*::-webkit-scrollbar-track {
  @apply bg-gray-100 dark:bg-gray-800;
}

*::-webkit-scrollbar-thumb {
  @apply bg-gray-400 dark:bg-gray-600 rounded-md;
}

*::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-500 dark:bg-gray-500;
}

/* Card game specific animations */
@keyframes card-glow {
  0%, 100% { box-shadow: 0 0 5px rgba(59, 130, 246, 0.5); }
  50% { box-shadow: 0 0 20px rgba(59, 130, 246, 0.8), 0 0 30px rgba(59, 130, 246, 0.6); }
}

.card-glow {
  animation: card-glow 2s ease-in-out infinite;
}
</style>
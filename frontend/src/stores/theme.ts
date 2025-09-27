import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

type Theme = 'dark' | 'light'

export const useThemeStore = defineStore('theme', () => {
  // Default to dark mode
  const isDark = ref<boolean>(true)

  // Initialize theme from localStorage or default to dark
  const initTheme = (): void => {
    const stored = localStorage.getItem('drawtwo-theme')
    if (stored) {
      isDark.value = stored === 'dark'
    } else {
      isDark.value = true // Default to dark mode
    }
    applyTheme()
  }

  // Apply theme to document
  const applyTheme = (): void => {
    if (isDark.value) {
      document.documentElement.classList.add('dark')
      document.documentElement.classList.remove('light')
    } else {
      document.documentElement.classList.add('light')
      document.documentElement.classList.remove('dark')
    }
  }

  // Toggle theme
  const toggleTheme = (): void => {
    isDark.value = !isDark.value
  }

  // Set specific theme
  const setTheme = (theme: Theme): void => {
    isDark.value = theme === 'dark'
  }

  // Watch for theme changes and persist to localStorage
  watch(isDark, (newValue: boolean) => {
    localStorage.setItem('drawtwo-theme', newValue ? 'dark' : 'light')
    applyTheme()
  })

  return {
    isDark,
    initTheme,
    toggleTheme,
    setTheme,
    applyTheme
  }
})

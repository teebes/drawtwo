import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  // Default to dark mode
  const isDark = ref(true)

  // Initialize theme from localStorage or default to dark
  const initTheme = () => {
    const stored = localStorage.getItem('drawtwo-theme')
    if (stored) {
      isDark.value = stored === 'dark'
    } else {
      isDark.value = true // Default to dark mode
    }
    applyTheme()
  }

  // Apply theme to document
  const applyTheme = () => {
    if (isDark.value) {
      document.documentElement.classList.add('dark')
      document.documentElement.classList.remove('light')
    } else {
      document.documentElement.classList.add('light')
      document.documentElement.classList.remove('dark')
    }
  }

  // Toggle theme
  const toggleTheme = () => {
    isDark.value = !isDark.value
  }

  // Set specific theme
  const setTheme = (theme) => {
    isDark.value = theme === 'dark'
  }

  // Watch for theme changes and persist to localStorage
  watch(isDark, (newValue) => {
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
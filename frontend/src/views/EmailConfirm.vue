<template>
  <div class="email-confirm">
    <div class="mx-auto flex min-h-screen w-full items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div class="w-full max-w-md space-y-8">
        <!-- Header -->
        <div class="text-center">
          <router-link to="/" class="inline-flex items-center">
            <h1 class="font-display text-3xl font-bold text-white">
              DrawTwo
            </h1>
            <img
              src="/drawtwo_logo.png"
              alt="DrawTwo Logo"
              class="ml-3 h-10 w-10 rounded-lg object-contain"
            />
          </router-link>
        </div>

        <!-- Main Card -->
        <div class="rounded-2xl bg-white p-8 shadow-xl dark:bg-gray-900">
          <!-- Loading State -->
          <div v-if="loading" class="text-center">
            <div class="mx-auto mb-6 h-16 w-16">
              <svg class="h-16 w-16 animate-spin text-primary-600" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <h2 class="mb-2 font-display text-2xl font-bold text-gray-900 dark:text-white">
              Confirming your email...
            </h2>
            <p class="text-gray-600 dark:text-gray-400">
              Please wait while we verify your email address.
            </p>
          </div>

          <!-- Success State -->
          <div v-else-if="success" class="text-center">
            <div class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
              <svg class="h-8 w-8 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
              </svg>
            </div>
            <h2 class="mb-2 font-display text-2xl font-bold text-gray-900 dark:text-white">
              Email Confirmed!
            </h2>
            <p class="mb-6 text-gray-600 dark:text-gray-400">
              Your email has been successfully verified and you are now logged in.
            </p>
            <div v-if="authStore.user" class="rounded-lg bg-green-50 p-4 dark:bg-green-900/20">
              <p class="font-medium text-green-800 dark:text-green-200">
                Welcome, <strong>{{ authStore.user.display_name }}</strong>!
              </p>
            </div>
            <div class="mt-6">
              <router-link
                to="/lobby"
                class="inline-flex w-full items-center justify-center rounded-lg bg-primary-600 px-4 py-3 text-sm font-medium text-white shadow-sm transition-all hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
              >
                Enter the Lobby
                <svg class="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                </svg>
              </router-link>
            </div>
          </div>

          <!-- Error State -->
          <div v-else class="text-center">
            <div class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
              <svg class="h-8 w-8 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </div>
            <h2 class="mb-2 font-display text-2xl font-bold text-gray-900 dark:text-white">
              Confirmation Failed
            </h2>
            <p class="mb-6 text-gray-600 dark:text-gray-400">
              {{ errorMessage }}
            </p>
            <div class="space-y-3">
              <router-link
                to="/login"
                class="inline-flex w-full items-center justify-center rounded-lg bg-primary-600 px-4 py-3 text-sm font-medium text-white shadow-sm transition-all hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
              >
                Back to Login
              </router-link>
              <router-link
                to="/"
                class="inline-flex w-full items-center justify-center rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-sm transition-all hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 dark:focus:ring-offset-gray-900"
              >
                Go Home
              </router-link>
            </div>
          </div>

          <!-- Footer -->
          <div class="mt-8 border-t border-gray-200 pt-6 text-center dark:border-gray-700">
            <p class="text-sm text-gray-500 dark:text-gray-400">
              Having trouble?
              <router-link to="/login" class="font-medium text-primary-600 transition-colors hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300">
                Contact support
              </router-link>
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const success = ref(false)
const errorMessage = ref('')

const confirmEmail = async () => {
  const key = route.params.key

  if (!key) {
    loading.value = false
    errorMessage.value = 'Invalid confirmation link. The confirmation key is missing.'
    return
  }

  try {
    const result = await authStore.confirmEmail(key)

    if (result.success) {
      success.value = true
      // Redirect to lobby after a short delay
      setTimeout(() => {
        router.push('/lobby')
      }, 3000)
    } else {
      errorMessage.value = result.error?.error || result.error?.message || 'Email confirmation failed. The link may be invalid or expired.'
    }
  } catch (error) {
    console.error('Email confirmation error:', error)
    errorMessage.value = 'An unexpected error occurred. Please try again later.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  confirmEmail()
})
</script>

<style scoped>
.email-confirm {
  min-height: 100vh;
  background: linear-gradient(135deg,
    theme('colors.primary.600') 0%,
    theme('colors.primary.700') 25%,
    theme('colors.secondary.600') 75%,
    theme('colors.secondary.700') 100%
  );
}
</style>
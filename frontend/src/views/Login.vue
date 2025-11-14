<template>
  <div class="gradient-primary-to-secondary-diagonal min-h-screen">
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
          <h2 class="mt-6 font-display text-2xl font-bold text-white">
            {{ isSignUp ? 'Create your account' : 'Welcome back' }}
          </h2>
          <p class="mt-2 text-sm text-primary-100">
            {{ isSignUp ? 'Join the trading card community' : 'Sign in to your account' }}
          </p>
        </div>

        <!-- Main Card -->
        <div class="rounded-2xl bg-white p-8 shadow-xl dark:bg-gray-900">
          <!-- Error/Success Messages -->
          <div v-if="message" class="mb-6 rounded-lg p-4" :class="{
            'bg-green-50 border border-green-200 text-green-800 dark:bg-green-900/30 dark:border-green-700 dark:text-green-200': messageType === 'success',
            'bg-red-50 border border-red-200 text-red-800 dark:bg-red-900/30 dark:border-red-700 dark:text-red-200': messageType === 'error',
            'bg-blue-50 border border-blue-200 text-blue-800 dark:bg-blue-900/30 dark:border-blue-700 dark:text-blue-200': messageType === 'info'
          }">
            {{ message }}
          </div>

          <!-- Login/Register Form -->
          <form @submit.prevent="handleSubmit" class="space-y-6">
            <div>
              <label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Email Address
              </label>
              <div class="mt-1">
                <input
                  id="email"
                  v-model="email"
                  type="email"
                  required
                  placeholder="Enter your email"
                  :disabled="authStore.loading"
                  class="block w-full rounded-lg border border-gray-300 px-3 py-3 text-gray-900 placeholder-gray-500 shadow-sm transition-all focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-gray-50 disabled:text-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400 dark:disabled:bg-gray-700"
                />
              </div>
            </div>

            <div v-if="isSignUp">
              <label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Username (Optional)
              </label>
              <div class="mt-1">
                <input
                  id="username"
                  v-model="username"
                  type="text"
                  placeholder="Choose a username for multiplayer"
                  :disabled="authStore.loading"
                  maxlength="150"
                  class="block w-full rounded-lg border border-gray-300 px-3 py-3 text-gray-900 placeholder-gray-500 shadow-sm transition-all focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-gray-50 disabled:text-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400 dark:disabled:bg-gray-700"
                />
              </div>
              <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Optional - you can add this later for multiplayer features
              </p>
            </div>

            <button
              type="submit"
              :disabled="authStore.loading || !email"
              class="flex w-full justify-center rounded-lg bg-primary-600 px-4 py-3 text-sm font-medium text-white shadow-sm transition-all hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-900"
            >
              <svg v-if="authStore.loading" class="mr-2 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ authStore.loading ? 'Please wait...' : (isSignUp ? 'Sign Up' : 'Send Login Link') }}
            </button>
          </form>

          <div class="relative mt-6">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-gray-300 dark:border-gray-600"></div>
            </div>
            <div class="relative flex justify-center text-sm">
              <span class="bg-white px-2 text-gray-500 dark:bg-gray-900 dark:text-gray-400">or</span>
            </div>
          </div>

          <!-- Google Login -->
          <button
            @click="handleGoogleLogin"
            :disabled="authStore.loading || !googleReady"
            class="mt-6 flex w-full items-center justify-center rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-sm transition-all hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 dark:focus:ring-offset-gray-900"
          >
            <svg class="mr-2 h-5 w-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            {{ googleReady ? 'Continue with Google' : 'Google login unavailable' }}
          </button>
          <p v-if="googleError" class="mt-2 text-center text-xs text-red-500 dark:text-red-400">
            {{ googleError }}
          </p>

          <!-- Toggle between Login/Register -->
          <div class="mt-6 text-center">
            <button
              @click="toggleMode"
              type="button"
              class="text-sm font-medium text-primary-600 transition-colors hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300"
            >
              {{ isSignUp ? 'Already have an account? Sign in' : 'New to DrawTwo? Create an account' }}
            </button>
          </div>

          <!-- Back to Home -->
          <div class="mt-4 text-center">
            <router-link
              to="/"
              class="inline-flex items-center text-sm font-medium text-gray-500 transition-colors hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            >
              <svg class="mr-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
              </svg>
              Back to Home
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

declare global {
  interface Window {
    google?: any
  }
}

type GoogleTokenClient = {
  requestAccessToken: (options?: { prompt?: string }) => void
}

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const username = ref('')
const isSignUp = ref(false)
const message = ref('')
const messageType = ref<'info' | 'success' | 'error'>('info')
const googleReady = ref(false)
const googleError = ref('')

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined
let tokenClient: GoogleTokenClient | null = null
let googleScriptPromise: Promise<void> | null = null

const showMessage = (text: string, type: 'info' | 'success' | 'error' = 'info') => {
  message.value = text
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 5000)
}

const toggleMode = () => {
  isSignUp.value = !isSignUp.value
  message.value = ''
}

const loadGoogleScript = (): Promise<void> => {
  if (window.google?.accounts?.oauth2) {
    return Promise.resolve()
  }

  if (googleScriptPromise) {
    return googleScriptPromise
  }

  googleScriptPromise = new Promise((resolve, reject) => {
    const existingScript = document.querySelector<HTMLScriptElement>('script[data-google-identity="true"]')

    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(), { once: true })
      existingScript.addEventListener('error', () => reject(new Error('Failed to load Google OAuth script')), { once: true })
      return
    }

    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.dataset.googleIdentity = 'true'
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load Google OAuth script'))
    document.head.appendChild(script)
  })

  return googleScriptPromise
}

const initGoogleClient = async () => {
  if (!googleClientId) {
    googleError.value = 'Google client ID is not configured.'
    googleReady.value = false
    return
  }

  try {
    await loadGoogleScript()

    tokenClient = window.google?.accounts?.oauth2?.initTokenClient({
      client_id: googleClientId,
      scope: 'profile email',
      callback: async (tokenResponse: { access_token?: string }) => {
        if (!tokenResponse?.access_token) {
          showMessage('Google did not return an access token. Please try again.', 'error')
          return
        }

        const result = await authStore.googleLogin(tokenResponse.access_token)
        if (result.success) {
          showMessage('Google login successful! Redirecting...', 'success')
          const redirect = (route.query.redirect as string) || '/play'
          setTimeout(() => {
            router.push(redirect)
          }, 800)
        } else {
          const errorMsg = result.error?.message || 'Google login failed'
          showMessage(errorMsg, 'error')
        }
      }
    }) as GoogleTokenClient

    googleReady.value = true
    googleError.value = ''
  } catch (error) {
    console.error('Failed to initialize Google login:', error)
    googleError.value = 'Unable to load Google login. Please refresh and try again.'
    googleReady.value = false
  }
}

onMounted(() => {
  initGoogleClient()
})

const handleSubmit = async () => {
  try {
    if (isSignUp.value) {
      // Registration
      const userData = {
        email: email.value,
        username: username.value || undefined
      }

      const result = await authStore.register(userData)

      if (result.success) {
        showMessage('Registration successful! Please check your email to verify your account.', 'success')
        // Switch to login mode
        isSignUp.value = false
      } else {
        const errorMsg = result.error?.email?.[0] || result.error?.message || 'Registration failed'
        showMessage(errorMsg, 'error')
      }
    } else {
      // Login
      const result = await authStore.sendLoginEmail(email.value)

      if (result.success) {
        showMessage('Login link sent! Please check your email and click the link to sign in.', 'success')
      } else {
        const errorMsg = result.error?.email?.[0] || result.error?.message || 'Failed to send login email'
        showMessage(errorMsg, 'error')
      }
    }
  } catch (error) {
    console.error('Auth error:', error)
    showMessage('Something went wrong. Please try again.', 'error')
  }
}

const handleGoogleLogin = async () => {
  if (!googleReady.value || !tokenClient) {
    if (googleError.value) {
      showMessage(googleError.value, 'error')
    } else {
      showMessage('Google login is not ready yet. Please try again shortly.', 'info')
    }
    return
  }

  try {
    tokenClient.requestAccessToken({ prompt: 'consent' })
  } catch (error) {
    console.error('Google login failed to start:', error)
    showMessage('Unable to start Google login. Please try again.', 'error')
  }
}
</script>

<style scoped>
/* .login {
  min-height: 100vh;
  background: linear-gradient(135deg,
    theme('colors.primary.600') 0%,
    theme('colors.primary.700') 25%,
    theme('colors.secondary.600') 75%,
    theme('colors.secondary.700') 100%
  );
} */
</style>
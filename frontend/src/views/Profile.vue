<template>
  <div class="profile flex flex-col">

      <!-- Profile Header -->
      <section class="bg-gray-300 h-24 flex items-center justify-center">
        <h1 class="font-display text-4xl font-bold dark:text-gray-900">Profile</h1>
      </section>

      <!-- Profile Content -->
      <section class="py-16">
        <div class="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <div class="grid gap-8">
            <!-- User Information -->
            <div class="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-900 sm:p-8">
              <h2 class="font-display text-2xl font-bold text-gray-900 dark:text-white mb-6">
                👤 Account Information
              </h2>

              <div v-if="authStore.user" class="space-y-4">
                <div class="flex items-center justify-between gap-3 py-3 border-b border-gray-200 dark:border-gray-700">
                  <span class="font-medium text-gray-700 dark:text-gray-300">Email:</span>
                  <span class="min-w-0 break-all text-right text-gray-900 dark:text-white">{{ authStore.user.email }}</span>
                </div>

                <div
                  class="flex gap-2 py-3 border-b border-gray-200 dark:border-gray-700"
                  :class="isEditingUsername ? 'flex-col sm:flex-row sm:items-center sm:justify-between' : 'items-center justify-between'"
                >
                  <span class="font-medium text-gray-700 dark:text-gray-300">Username:</span>
                  <div
                    class="flex items-center gap-2"
                    :class="isEditingUsername ? 'w-full sm:w-auto' : 'w-auto'"
                  >
                    <template v-if="isEditingUsername">
                      <div class="flex w-full flex-col items-stretch gap-1 sm:w-auto sm:items-end">
                        <div class="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
                          <input
                            v-model="newUsername"
                            type="text"
                            class="w-full min-w-0 rounded-md border-gray-300 px-2 py-1 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:w-48 sm:text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-white"
                            placeholder="Enter username"
                            @keyup.enter="saveUsername"
                            @keyup.esc="cancelEdit"
                          />
                          <div class="grid grid-cols-2 gap-2 sm:flex">
                            <button
                              @click="saveUsername"
                              :disabled="authStore.loading"
                              class="inline-flex items-center justify-center rounded bg-indigo-600 px-2 py-1 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50"
                            >
                              Save
                            </button>
                            <button
                              @click="cancelEdit"
                              class="inline-flex items-center justify-center rounded bg-white px-2 py-1 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:ring-gray-600 dark:hover:bg-gray-600"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                        <span v-if="authStore.error?.username" class="text-xs text-red-600">
                          {{ Array.isArray(authStore.error.username) ? authStore.error.username[0] : authStore.error.username }}
                        </span>
                      </div>
                    </template>
                    <template v-else>
                      <span class="min-w-0 break-all text-gray-900 dark:text-white">{{ authStore.user.username }}</span>
                      <button
                        @click="startEdit"
                        class="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
                      >
                        {{ authStore.user.username ? 'Edit' : 'Set' }}
                      </button>
                    </template>
                  </div>
                </div>

                <div class="flex items-center justify-between gap-3 py-3 border-b border-gray-200 dark:border-gray-700">
                  <span class="font-medium text-gray-700 dark:text-gray-300">Member Since:</span>
                  <span class="text-right text-gray-900 dark:text-white">{{ formatDate(authStore.user.created_at) }}</span>
                </div>

                <div class="flex items-center justify-between gap-3 py-3 border-b border-gray-200 dark:border-gray-700">
                  <span class="font-medium text-gray-700 dark:text-gray-300">Apple:</span>
                  <div class="flex min-w-0 items-center justify-end">
                    <div v-if="appleConnected" class="flex items-center gap-3">
                      <span
                        class="inline-flex items-center gap-1.5 text-sm font-medium text-green-700 dark:text-green-300"
                      >
                        <CheckCircle class="h-4 w-4" aria-hidden="true" />
                        Connected
                      </span>
                      <button
                        type="button"
                        @click="disconnectProvider('apple')"
                        :disabled="authStore.loading"
                        class="inline-flex items-center justify-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-600 dark:hover:bg-gray-700"
                      >
                        <Unlink class="h-4 w-4" aria-hidden="true" />
                        Disconnect
                      </button>
                    </div>
                    <button
                      v-else
                      type="button"
                      @click="connectApple"
                      :disabled="authStore.loading || !appleClientId"
                      class="inline-flex items-center justify-center gap-1.5 rounded-md bg-black px-3 py-1.5 text-sm font-semibold text-white shadow-sm transition hover:bg-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100"
                    >
                      <Loader2 v-if="authStore.loading" class="h-4 w-4 animate-spin" aria-hidden="true" />
                      <LinkIcon v-else class="h-4 w-4" aria-hidden="true" />
                      {{ appleClientId ? 'Connect Apple' : 'Apple unavailable' }}
                    </button>
                  </div>
                </div>

                <div class="flex items-center justify-between gap-3 py-3 border-b border-gray-200 dark:border-gray-700">
                  <span class="font-medium text-gray-700 dark:text-gray-300">Google:</span>
                  <div class="flex min-w-0 items-center justify-end">
                    <div v-if="googleConnected" class="flex items-center gap-3">
                      <span
                        class="inline-flex items-center gap-1.5 text-sm font-medium text-green-700 dark:text-green-300"
                      >
                        <CheckCircle class="h-4 w-4" aria-hidden="true" />
                        Connected
                      </span>
                      <button
                        type="button"
                        @click="disconnectProvider('google')"
                        :disabled="authStore.loading"
                        class="inline-flex items-center justify-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-600 dark:hover:bg-gray-700"
                      >
                        <Unlink class="h-4 w-4" aria-hidden="true" />
                        Disconnect
                      </button>
                    </div>
                    <span
                      v-else
                      class="text-sm font-medium text-gray-500 dark:text-gray-400"
                    >
                      Not connected
                    </span>
                  </div>
                </div>

                <div class="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
                  <span class="font-medium text-gray-700 dark:text-gray-300">Account:</span>
                  <button
                    type="button"
                    @click="deleteAccount"
                    :disabled="authStore.loading"
                    class="inline-flex items-center justify-center gap-1.5 rounded-md bg-red-600 px-3 py-1.5 text-sm font-semibold text-white shadow-sm transition hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Trash2 class="h-4 w-4" aria-hidden="true" />
                    Delete Account
                  </button>
                </div>

              </div>

              <p v-if="appleStatus" class="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800 dark:border-green-700 dark:bg-green-900/30 dark:text-green-200">
                {{ appleStatus }}
              </p>
              <p v-if="appleError" class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-700 dark:bg-red-900/30 dark:text-red-200">
                {{ appleError }}
              </p>
            </div>
          </div>
        </div>
      </section>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { CheckCircle, Link as LinkIcon, Loader2, Trash2, Unlink } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import {
  isAppleSignInCancellation,
  requestAppleCredential
} from '../utils/appleSignIn'

const authStore = useAuthStore()
const router = useRouter()
const isEditingUsername = ref(false)
const newUsername = ref('')
const appleStatus = ref('')
const appleError = ref('')

const appleClientId = import.meta.env.VITE_APPLE_SIGN_IN_CLIENT_ID as string | undefined
const appleRedirectUri = (import.meta.env.VITE_APPLE_REDIRECT_URI as string | undefined)
  || `${window.location.origin}/auth/callback/apple`
const appleConnected = computed(() => Boolean(authStore.user?.apple_connected))
const googleConnected = computed(() => Boolean(authStore.user?.google_connected))

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const startEdit = () => {
  newUsername.value = authStore.user?.username || ''
  isEditingUsername.value = true
}

const cancelEdit = () => {
  isEditingUsername.value = false
  newUsername.value = ''
  // Clear any errors
  authStore.error = null
}

const saveUsername = async () => {
  if (!newUsername.value.trim()) return

  const result = await authStore.updateProfile({ username: newUsername.value })
  if (result.success) {
    isEditingUsername.value = false
  }
}

const connectApple = async () => {
  appleStatus.value = ''
  appleError.value = ''

  if (!appleClientId) {
    appleError.value = 'Apple sign-in is not configured.'
    return
  }

  try {
    const credential = await requestAppleCredential(appleClientId, appleRedirectUri)
    const result = await authStore.linkApple(
      credential.identityToken,
      credential.authorizationCode,
      appleRedirectUri
    )

    if (result.success) {
      appleStatus.value = result.data?.message || 'Apple sign-in connected.'
      return
    }

    appleError.value = result.error?.error
      || result.error?.detail
      || result.error?.message
      || 'Apple account linking failed.'
  } catch (error: any) {
    if (isAppleSignInCancellation(error)) {
      return
    }

    appleError.value = error?.message || 'Unable to connect Apple sign-in.'
  }
}

const disconnectProvider = async (provider: 'apple' | 'google') => {
  appleStatus.value = ''
  appleError.value = ''

  const result = await authStore.disconnectSocial(provider)
  if (result.success) {
    appleStatus.value = result.data?.message || `${provider} sign-in disconnected.`
    return
  }

  appleError.value = result.error?.error
    || result.error?.detail
    || result.error?.message
    || `Unable to disconnect ${provider} sign-in.`
}

const deleteAccount = async () => {
  appleStatus.value = ''
  appleError.value = ''

  const confirmed = window.confirm(
    'Delete your Draw Two account? This removes your login access and profile information.'
  )
  if (!confirmed) {
    return
  }

  const result = await authStore.deleteAccount()
  if (result.success) {
    await router.push('/')
    return
  }

  appleError.value = result.error?.error
    || result.error?.detail
    || result.error?.message
    || 'Unable to delete account.'
}

onMounted(async () => {
  // Refresh user data when component mounts
  if (authStore.isAuthenticated) {
    await authStore.getCurrentUser()
  }
})
</script>

<style scoped>
</style>

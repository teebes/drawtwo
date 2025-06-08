<template>
  <div class="dashboard">
    <AppHeader />

    <main class="flex-1">
      <!-- Dashboard Header -->
      <section class="bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="text-center">
            <h1 class="font-display text-4xl font-bold text-white sm:text-5xl">
              Admin Dashboard
            </h1>
            <p class="mt-4 text-xl text-primary-100">
              System administration and monitoring
            </p>
          </div>
        </div>
      </section>

      <!-- Dashboard Content -->
      <section class="py-16">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="grid gap-8 lg:grid-cols-2">

            <!-- Authentication Test -->
            <div class="rounded-2xl bg-white p-8 shadow-sm dark:bg-gray-900">
              <div class="mb-4 flex items-center">
                <div class="rounded-lg bg-blue-100 p-3 dark:bg-blue-900/50">
                  <svg class="h-6 w-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                  </svg>
                </div>
                <div class="ml-4">
                  <h2 class="font-display text-xl font-semibold text-gray-900 dark:text-white">
                    Authentication Test
                  </h2>
                  <p class="text-gray-600 dark:text-gray-400">
                    Test protected API endpoints
                  </p>
                </div>
              </div>

              <p class="mb-6 text-gray-600 dark:text-gray-400">
                Verify that authentication is working correctly by testing the protected API endpoint.
              </p>

              <button
                @click="testProtectedAPI"
                :disabled="testing"
                class="inline-flex w-full items-center justify-center rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white shadow-sm transition-all hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 dark:focus:ring-offset-gray-900"
              >
                <svg v-if="testing" class="mr-2 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ testing ? 'Testing...' : 'Test Protected Endpoint' }}
              </button>

              <div v-if="apiTestResult" class="mt-6 rounded-lg p-4" :class="{
                'bg-green-50 border border-green-200 dark:bg-green-900/30 dark:border-green-700': apiTestSuccess,
                'bg-red-50 border border-red-200 dark:bg-red-900/30 dark:border-red-700': !apiTestSuccess
              }">
                <h4 class="mb-2 font-medium" :class="{
                  'text-green-800 dark:text-green-200': apiTestSuccess,
                  'text-red-800 dark:text-red-200': !apiTestSuccess
                }">
                  {{ apiTestSuccess ? '✅ Success' : '❌ Error' }}
                </h4>
                <pre class="overflow-x-auto text-xs" :class="{
                  'text-green-700 dark:text-green-300': apiTestSuccess,
                  'text-red-700 dark:text-red-300': !apiTestSuccess
                }">{{ JSON.stringify(apiTestResult, null, 2) }}</pre>
              </div>
            </div>

            <!-- System Status -->
            <div class="rounded-2xl bg-white p-8 shadow-sm dark:bg-gray-900">
              <div class="mb-4 flex items-center">
                <div class="rounded-lg bg-green-100 p-3 dark:bg-green-900/50">
                  <svg class="h-6 w-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                  </svg>
                </div>
                <div class="ml-4">
                  <h2 class="font-display text-xl font-semibold text-gray-900 dark:text-white">
                    System Status
                  </h2>
                  <p class="text-gray-600 dark:text-gray-400">
                    Monitor system health
                  </p>
                </div>
              </div>

              <div class="space-y-4">
                <div class="flex items-center justify-between rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
                  <div class="flex items-center">
                    <div class="h-2 w-2 rounded-full bg-green-500"></div>
                    <span class="ml-3 font-medium text-gray-900 dark:text-white">Authentication</span>
                  </div>
                  <span class="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200">
                    ✅ Active
                  </span>
                </div>

                <div class="flex items-center justify-between rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
                  <div class="flex items-center">
                    <div class="h-2 w-2 rounded-full bg-green-500"></div>
                    <span class="ml-3 font-medium text-gray-900 dark:text-white">JWT Token</span>
                  </div>
                  <span class="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200">
                    ✅ Valid
                  </span>
                </div>

                <div class="flex items-center justify-between rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
                  <div class="flex items-center">
                    <div class="h-2 w-2 rounded-full bg-yellow-500"></div>
                    <span class="ml-3 font-medium text-gray-900 dark:text-white">WebSocket</span>
                  </div>
                  <span class="inline-flex items-center rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                    🔶 Not Implemented
                  </span>
                </div>

                <div class="flex items-center justify-between rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
                  <div class="flex items-center">
                    <div class="h-2 w-2 rounded-full bg-green-500"></div>
                    <span class="ml-3 font-medium text-gray-900 dark:text-white">Database</span>
                  </div>
                  <span class="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200">
                    ✅ Connected
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import AppHeader from '../components/AppHeader.vue'

const authStore = useAuthStore()

const testing = ref(false)
const apiTestResult = ref(null)
const apiTestSuccess = ref(false)

const testProtectedAPI = async () => {
  testing.value = true
  apiTestResult.value = null

  try {
    const result = await authStore.testProtectedEndpoint()
    apiTestResult.value = result.data || result.error
    apiTestSuccess.value = result.success
  } catch (error) {
    apiTestResult.value = error
    apiTestSuccess.value = false
  } finally {
    testing.value = false
  }
}

onMounted(async () => {
  // Refresh user data when component mounts
  if (authStore.isAuthenticated) {
    await authStore.getCurrentUser()
  }
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
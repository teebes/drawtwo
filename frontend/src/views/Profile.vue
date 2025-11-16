<template>
  <div class="profile">
    <main class="flex-1">
      <!-- Profile Header -->
      <section class="bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="text-center">
            <h1 class="font-display text-4xl font-bold text-white sm:text-5xl">
              Your Profile
            </h1>
            <p class="mt-4 text-xl text-primary-100" v-if="authStore.user">
              Welcome back, {{ authStore.user.display_name }}!
            </p>
          </div>
        </div>
      </section>

      <!-- Profile Content -->
      <section class="py-16">
        <div class="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <div :class="['grid gap-8', authStore.user?.is_staff ? 'lg:grid-cols-2' : '']">

            <!-- User Information -->
            <div class="rounded-2xl bg-white p-8 shadow-sm dark:bg-gray-900">
              <h2 class="font-display text-2xl font-bold text-gray-900 dark:text-white mb-6">
                👤 Account Information
              </h2>

              <div v-if="authStore.user" class="space-y-4">
                <div class="flex items-center justify-between py-3 border-b border-gray-200 dark:border-gray-700">
                  <span class="font-medium text-gray-700 dark:text-gray-300">Email:</span>
                  <span class="text-gray-900 dark:text-white">{{ authStore.user.email }}</span>
                </div>

                <div v-if="authStore.user.username" class="flex items-center justify-between py-3 border-b border-gray-200 dark:border-gray-700">
                  <span class="font-medium text-gray-700 dark:text-gray-300">Username:</span>
                  <span class="text-gray-900 dark:text-white">{{ authStore.user.username }}</span>
                </div>

                <div class="flex items-center justify-between py-3 border-b border-gray-200 dark:border-gray-700">
                  <span class="font-medium text-gray-700 dark:text-gray-300">Email Status:</span>
                  <span :class="{
                    'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium': true,
                    'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200': authStore.user.is_email_verified,
                    'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200': !authStore.user.is_email_verified
                  }">
                    {{ authStore.user.is_email_verified ? '✅ Verified' : '❌ Not Verified' }}
                  </span>
                </div>

                <div class="flex items-center justify-between py-3 border-b border-gray-200 dark:border-gray-700">
                  <span class="font-medium text-gray-700 dark:text-gray-300">Member Since:</span>
                  <span class="text-gray-900 dark:text-white">{{ formatDate(authStore.user.created_at) }}</span>
                </div>


                <div v-if="authStore.user.is_staff" class="flex items-center justify-between py-3">
                  <span class="font-medium text-gray-700 dark:text-gray-300">Account Type:</span>
                  <span class="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800 dark:bg-purple-900 dark:text-purple-200">
                    🛡️ Staff Member
                  </span>
                </div>
              </div>
            </div>

            <!-- Administrative shortcuts -->
            <div
              v-if="authStore.user?.is_staff"
              class="rounded-2xl bg-white p-8 shadow-sm dark:bg-gray-900"
            >
              <h2 class="font-display text-2xl font-bold text-gray-900 dark:text-white mb-6">
                🛡️ Administrative Access
              </h2>

              <p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Manage DrawTwo systems and content from these quick links.
              </p>

              <div class="space-y-3">
                <router-link
                  to="/dashboard"
                  class="flex items-center justify-between rounded-xl bg-purple-600 px-4 py-3 text-sm font-medium text-white shadow-sm transition-all hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
                >
                  Admin Dashboard
                  <svg class="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                  </svg>
                </router-link>

                <router-link
                  to="/control"
                  class="flex items-center justify-between rounded-xl bg-purple-600 px-4 py-3 text-sm font-medium text-white shadow-sm transition-all hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
                >
                  Control Panel
                  <svg class="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                  </svg>
                </router-link>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

onMounted(async () => {
  // Refresh user data when component mounts
  if (authStore.isAuthenticated) {
    await authStore.getCurrentUser()
  }
})
</script>

<style scoped>
.profile {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
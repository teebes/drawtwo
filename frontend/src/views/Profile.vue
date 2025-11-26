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
          </div>
        </div>
      </section>

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
</style>
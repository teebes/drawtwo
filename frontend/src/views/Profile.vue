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

                <div class="flex items-center justify-between py-3 border-b border-gray-200 dark:border-gray-700">
                  <span class="font-medium text-gray-700 dark:text-gray-300">Username:</span>
                  <div class="flex items-center gap-2">
                    <template v-if="isEditingUsername">
                      <div class="flex flex-col items-end gap-1">
                        <div class="flex gap-2">
                          <input
                            v-model="newUsername"
                            type="text"
                            class="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-white px-2 py-1"
                            placeholder="Enter username"
                            @keyup.enter="saveUsername"
                            @keyup.esc="cancelEdit"
                          />
                          <button
                            @click="saveUsername"
                            :disabled="authStore.loading"
                            class="inline-flex items-center rounded bg-indigo-600 px-2 py-1 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50"
                          >
                            Save
                          </button>
                          <button
                            @click="cancelEdit"
                            class="inline-flex items-center rounded bg-white px-2 py-1 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:ring-gray-600 dark:hover:bg-gray-600"
                          >
                            Cancel
                          </button>
                        </div>
                        <span v-if="authStore.error?.username" class="text-xs text-red-600">
                          {{ Array.isArray(authStore.error.username) ? authStore.error.username[0] : authStore.error.username }}
                        </span>
                      </div>
                    </template>
                    <template v-else>
                      <span class="text-gray-900 dark:text-white">{{ authStore.user.username }}</span>
                      <button
                        @click="startEdit"
                        class="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
                      >
                        {{ authStore.user.username ? 'Edit' : 'Set' }}
                      </button>
                    </template>
                  </div>
                </div>

                <div class="flex items-center justify-between py-3 border-b border-gray-200 dark:border-gray-700">
                  <span class="font-medium text-gray-700 dark:text-gray-300">Member Since:</span>
                  <span class="text-gray-900 dark:text-white">{{ formatDate(authStore.user.created_at) }}</span>
                </div>


              </div>
            </div>
          </div>
        </div>
      </section>

  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const isEditingUsername = ref(false)
const newUsername = ref('')

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

onMounted(async () => {
  // Refresh user data when component mounts
  if (authStore.isAuthenticated) {
    await authStore.getCurrentUser()
  }
})
</script>

<style scoped>
</style>
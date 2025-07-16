<template>
  <div class="user-management">
    <Panel title="User Management">

      <!-- Filters and Search -->
      <div class="mb-6 flex flex-col sm:flex-row gap-4">
        <!-- Search -->
        <div class="flex-1">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by email or username..."
            class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            @input="debouncedSearch"
          />
        </div>

        <!-- Status Filter -->
        <div class="sm:w-48">
          <select
            v-model="statusFilter"
            @change="fetchUsers"
            class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          >
            <option value="">All Status</option>
            <option
              v-for="status in USER_STATUS_CHOICES"
              :key="status.value"
              :value="status.value"
            >
              {{ status.label }}
            </option>
          </select>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <div class="text-gray-600 dark:text-gray-300">Loading users...</div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="mb-6">
        <div class="rounded-md bg-red-50 dark:bg-red-900 p-4">
          <div class="text-sm text-red-700 dark:text-red-200">
            {{ error }}
          </div>
        </div>
      </div>

      <!-- Users Table -->
      <div v-else class="overflow-x-auto shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
        <table class="min-w-full divide-y divide-gray-300 dark:divide-gray-600">
          <thead class="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                User
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Status
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Joined
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Last Login
              </th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-for="user in users" :key="user.id" class="hover:bg-gray-50 dark:hover:bg-gray-800">
              <!-- User Info -->
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                  <div class="flex-shrink-0 h-10 w-10">
                    <div class="h-10 w-10 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                      <span class="text-sm font-medium text-primary-700 dark:text-primary-300">
                        {{ user.display_name.charAt(0).toUpperCase() }}
                      </span>
                    </div>
                  </div>
                  <div class="ml-4">
                    <div class="text-sm font-medium text-gray-900 dark:text-white">
                      {{ user.display_name }}
                    </div>
                    <div class="text-sm text-gray-500 dark:text-gray-400">
                      {{ user.email }}
                    </div>
                  </div>
                </div>
              </td>

              <!-- Status -->
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center space-x-2">
                  <select
                    :value="user.status"
                    @change="updateUserStatus(user, ($event.target as HTMLSelectElement).value)"
                    :disabled="updatingUser === user.id"
                    class="text-xs px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    :class="USER_STATUS_COLORS[user.status].replace('bg-', 'border-').replace('text-', 'text-').split(' ')[1]"
                  >
                    <option
                      v-for="status in USER_STATUS_CHOICES"
                      :key="status.value"
                      :value="status.value"
                    >
                      {{ status.label }}
                    </option>
                  </select>

                  <!-- Loading indicator when updating -->
                  <div v-if="updatingUser === user.id" class="flex items-center">
                    <svg class="animate-spin h-3 w-3 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                </div>
              </td>

                            <!-- Joined Date -->
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                {{ formatDateShort(user.created_at) }}
              </td>

              <!-- Last Login -->
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                {{ user.last_login ? formatDateShort(user.last_login) : 'Never' }}
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Empty State -->
        <div v-if="users.length === 0" class="text-center py-8">
          <div class="text-gray-500 dark:text-gray-400">
            No users found matching your criteria
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="pagination && pagination.count > 0" class="mt-6 flex items-center justify-between">
        <div class="text-sm text-gray-700 dark:text-gray-300">
          Showing {{ users.length }} of {{ pagination.count }} users
        </div>

        <div class="flex space-x-2">
          <GameButton
            v-if="pagination.previous"
            @click="loadPage(pagination.previous)"
            variant="secondary"
            size="sm"
            :disabled="loading"
          >
            Previous
          </GameButton>

          <GameButton
            v-if="pagination.next"
            @click="loadPage(pagination.next)"
            variant="secondary"
            size="sm"
            :disabled="loading"
          >
            Next
          </GameButton>
        </div>
      </div>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from '../../config/api'
import Panel from '../layout/Panel.vue'
import GameButton from '../ui/GameButton.vue'
import type { User, PaginatedResponse } from '../../types/control'
import { USER_STATUS_CHOICES, USER_STATUS_COLORS } from '../../types/control'

const loading = ref(true)
const error = ref<string | null>(null)
const users = ref<User[]>([])
const pagination = ref<PaginatedResponse<User> | null>(null)
const searchQuery = ref('')
const statusFilter = ref('')
const updatingUser = ref<number | null>(null)

// Debounce search
let searchTimeout: number | null = null

const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    fetchUsers()
  }, 500)
}

const fetchUsers = async (url?: string) => {
  try {
    loading.value = true
    error.value = null

    // Build query parameters
    const params = new URLSearchParams()
    if (searchQuery.value) params.append('search', searchQuery.value)
    if (statusFilter.value) params.append('status', statusFilter.value)

    const requestUrl = url || `/control/users/?${params.toString()}`
    const response = await axios.get(requestUrl)

    pagination.value = response.data
    users.value = response.data.results
  } catch (err: any) {
    error.value = err.response?.data?.error || 'Failed to load users'
  } finally {
    loading.value = false
  }
}

const loadPage = (url: string) => {
  fetchUsers(url)
}

const updateUserStatus = async (user: User, newStatus: string) => {
  try {
    updatingUser.value = user.id

    const response = await axios.patch(`/control/users/${user.id}/status/`, {
      status: newStatus
    })

    // Update the user in the list
    const userIndex = users.value.findIndex(u => u.id === user.id)
    if (userIndex !== -1) {
      users.value[userIndex] = response.data
    }
  } catch (err: any) {
    error.value = err.response?.data?.error || 'Failed to update user status'
    // Revert the select to original value on error
    fetchUsers()
  } finally {
    updatingUser.value = null
  }
}

const formatDateShort = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString()
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.user-management {
  /* Custom styles if needed */
}
</style>
<template>
  <div class="overview-dashboard">
    <div v-if="loading" class="text-center py-8">
      <div class="text-gray-600 dark:text-gray-300">Loading...</div>
    </div>

    <div v-else-if="error" class="mb-6">
      <Panel variant="error">
        <p>{{ error }}</p>
      </Panel>
    </div>

    <div v-else>
      <!-- Quick Stats -->
      <div class="grid gap-6 mb-8 md:grid-cols-3">
        <Panel title="Total Users">
          <div class="text-3xl font-bold text-primary-600 dark:text-primary-400">
            {{ overview?.quick_stats.total_users || 0 }}
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Registered users
          </p>
        </Panel>

        <Panel title="New Users (7 days)">
          <div class="text-3xl font-bold text-green-600 dark:text-green-400">
            {{ overview?.quick_stats.users_last_week || 0 }}
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Recent signups
          </p>
        </Panel>

        <Panel title="Pending Approval">
          <div class="text-3xl font-bold text-yellow-600 dark:text-yellow-400">
            {{ overview?.quick_stats.pending_users || 0 }}
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Awaiting approval
          </p>
        </Panel>
      </div>

      <!-- Site Status -->
      <div class="grid gap-6 lg:grid-cols-2">
        <Panel title="Site Access Controls">
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium">Whitelist Mode</span>
              <span
                :class="[
                  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                  overview?.site_settings.whitelist_mode_enabled
                    ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                ]"
              >
                {{ overview?.site_settings.whitelist_mode_enabled ? 'ENABLED' : 'DISABLED' }}
              </span>
            </div>

            <div class="flex items-center justify-between">
              <span class="text-sm font-medium">User Signups</span>
              <span
                :class="[
                  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                  overview?.site_settings.signup_disabled
                    ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                ]"
              >
                {{ overview?.site_settings.signup_disabled ? 'DISABLED' : 'ENABLED' }}
              </span>
            </div>
          </div>
        </Panel>

        <Panel title="Recent Activity">
          <div class="space-y-3">
            <div v-if="recentUsers && recentUsers.length > 0">
              <div
                v-for="user in recentUsers.slice(0, 5)"
                :key="user.id"
                class="flex items-center justify-between py-2"
              >
                <div>
                  <div class="text-sm font-medium text-gray-900 dark:text-white">
                    {{ user.display_name }}
                  </div>
                  <div class="text-xs text-gray-500 dark:text-gray-400">
                    {{ formatDate(user.created_at) }}
                  </div>
                </div>
                <span
                  :class="[
                    'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                    USER_STATUS_COLORS[user.status]
                  ]"
                >
                  {{ user.status_display || user.status }}
                </span>
              </div>
            </div>
            <div v-else class="text-sm text-gray-500 dark:text-gray-400">
              No recent activity
            </div>
          </div>
        </Panel>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from '../../config/api'
import Panel from '../layout/Panel.vue'
import type { ControlPanelOverview, User } from '../../types/control'
import { USER_STATUS_COLORS } from '../../types/control'

const loading = ref(true)
const error = ref<string | null>(null)
const overview = ref<ControlPanelOverview | null>(null)
const recentUsers = ref<User[] | null>(null)

const fetchOverview = async () => {
  try {
    loading.value = true
    error.value = null

    const [overviewResponse, recentUsersResponse] = await Promise.all([
      axios.get('/control/overview/'),
      axios.get('/control/users/recent/')
    ])

    overview.value = overviewResponse.data
    recentUsers.value = recentUsersResponse.data
  } catch (err: any) {
    error.value = err.response?.data?.error || 'Failed to load overview data'
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  fetchOverview()
})
</script>

<style scoped>
.overview-dashboard {
  /* Custom styles if needed */
}
</style>
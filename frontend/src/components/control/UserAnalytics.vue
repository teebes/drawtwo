<template>
  <div class="user-analytics">
    <div v-if="loading" class="text-center py-8">
      <div class="text-gray-600 dark:text-gray-300">Loading analytics...</div>
    </div>

    <div v-else-if="error" class="mb-6">
      <Panel variant="error">
        <p>{{ error }}</p>
      </Panel>
    </div>

    <div v-else>
      <!-- Summary Stats -->
      <div class="grid gap-6 mb-8 md:grid-cols-2 lg:grid-cols-4">
        <Panel title="Total Users">
          <div class="text-3xl font-bold text-primary-600 dark:text-primary-400">
            {{ analytics?.total_users || 0 }}
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            All registered users
          </p>
        </Panel>

        <Panel title="New Users (7 days)">
          <div class="text-3xl font-bold text-green-600 dark:text-green-400">
            {{ analytics?.users_last_week || 0 }}
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Recent signups
          </p>
        </Panel>

        <Panel title="Pending Approval">
          <div class="text-3xl font-bold text-yellow-600 dark:text-yellow-400">
            {{ analytics?.pending_users || 0 }}
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Awaiting approval
          </p>
        </Panel>

        <Panel title="Approved Users">
          <div class="text-3xl font-bold text-green-600 dark:text-green-400">
            {{ analytics?.approved_users || 0 }}
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Active users
          </p>
        </Panel>
      </div>

      <!-- Status Breakdown -->
      <div class="grid gap-6 lg:grid-cols-2 mb-8">
        <Panel title="User Status Breakdown">
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <span class="inline-block w-3 h-3 rounded-full bg-yellow-400 mr-2"></span>
                <span class="text-sm font-medium">Pending</span>
              </div>
              <span class="text-sm text-gray-600 dark:text-gray-400">
                {{ analytics?.pending_users || 0 }}
              </span>
            </div>

            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <span class="inline-block w-3 h-3 rounded-full bg-green-400 mr-2"></span>
                <span class="text-sm font-medium">Approved</span>
              </div>
              <span class="text-sm text-gray-600 dark:text-gray-400">
                {{ analytics?.approved_users || 0 }}
              </span>
            </div>

            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <span class="inline-block w-3 h-3 rounded-full bg-orange-400 mr-2"></span>
                <span class="text-sm font-medium">Suspended</span>
              </div>
              <span class="text-sm text-gray-600 dark:text-gray-400">
                {{ analytics?.suspended_users || 0 }}
              </span>
            </div>

            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <span class="inline-block w-3 h-3 rounded-full bg-red-400 mr-2"></span>
                <span class="text-sm font-medium">Banned</span>
              </div>
              <span class="text-sm text-gray-600 dark:text-gray-400">
                {{ analytics?.banned_users || 0 }}
              </span>
            </div>
          </div>
        </Panel>

        <Panel title="Signup Trend (Last 7 Days)">
          <div class="space-y-3">
            <div
              v-for="day in analytics?.recent_signups || []"
              :key="day.date"
              class="flex items-center justify-between"
            >
              <span class="text-sm text-gray-600 dark:text-gray-400">
                {{ formatDateShort(day.date) }}
              </span>
              <div class="flex items-center">
                <div
                  class="h-2 bg-primary-500 rounded mr-2"
                  :style="{ width: `${Math.max(day.count * 20, 4)}px` }"
                ></div>
                <span class="text-sm font-medium">{{ day.count }}</span>
              </div>
            </div>

            <div v-if="!analytics?.recent_signups?.length" class="text-sm text-gray-500 dark:text-gray-400">
              No signup data available
            </div>
          </div>
        </Panel>
      </div>

      <!-- Detailed Breakdown -->
      <Panel title="Detailed Statistics">
        <div class="grid gap-6 md:grid-cols-3">
          <div class="text-center p-6 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div class="text-2xl font-bold text-gray-900 dark:text-white">
              {{ calculateApprovalRate() }}%
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              Approval Rate
            </div>
          </div>

          <div class="text-center p-6 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div class="text-2xl font-bold text-gray-900 dark:text-white">
              {{ calculateWeeklyGrowth() }}%
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              Weekly Growth
            </div>
          </div>

          <div class="text-center p-6 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div class="text-2xl font-bold text-gray-900 dark:text-white">
              {{ calculateActiveUsers() }}
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              Active Users
            </div>
          </div>
        </div>
      </Panel>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from '../../config/api'
import Panel from '../layout/Panel.vue'
import type { UserAnalytics } from '../../types/control'

const loading = ref(true)
const error = ref<string | null>(null)
const analytics = ref<UserAnalytics | null>(null)

const fetchAnalytics = async () => {
  try {
    loading.value = true
    error.value = null

    const response = await axios.get('/control/analytics/')
    analytics.value = response.data
  } catch (err: any) {
    error.value = err.response?.data?.error || 'Failed to load analytics data'
  } finally {
    loading.value = false
  }
}

const formatDateShort = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

const calculateApprovalRate = () => {
  if (!analytics.value) return 0
  const total = analytics.value.total_users
  const approved = analytics.value.approved_users
  return total > 0 ? Math.round((approved / total) * 100) : 0
}

const calculateWeeklyGrowth = () => {
  if (!analytics.value) return 0
  const total = analytics.value.total_users
  const weekly = analytics.value.users_last_week
  const previousTotal = total - weekly
  return previousTotal > 0 ? Math.round((weekly / previousTotal) * 100) : 0
}

const calculateActiveUsers = () => {
  if (!analytics.value) return 0
  return analytics.value.approved_users + analytics.value.pending_users
}

onMounted(() => {
  fetchAnalytics()
})
</script>

<style scoped>
.user-analytics {
  /* Custom styles if needed */
}
</style>
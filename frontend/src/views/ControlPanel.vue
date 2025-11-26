<template>
  <div class="control-panel min-h-screen bg-gray-50 dark:bg-gray-900">
    <div class="py-8">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <!-- Header -->
        <header class="mb-8">
          <h1 class="font-display text-3xl font-bold text-gray-900 dark:text-white lg:text-4xl">
            Control Panel
          </h1>
          <p class="mt-2 text-lg text-gray-600 dark:text-gray-300">
            Site administration and user management
          </p>
        </header>

        <!-- Navigation Tabs -->
        <div class="mb-8 overflow-hidden">
          <div class="overflow-x-auto pb-2 -mb-2">
            <nav class="flex space-x-8 border-b border-gray-200 dark:border-gray-700" aria-label="Tabs">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                @click="activeTab = tab.id"
                :class="[
                  'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200',
                  activeTab === tab.id
                    ? 'border-primary-600 text-primary-600 dark:border-primary-400 dark:text-primary-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 hover:border-gray-300'
                ]"
              >
                {{ tab.name }}
              </button>
            </nav>
          </div>
        </div>

        <!-- Tab Content -->
        <div v-if="activeTab === 'overview'">
          <OverviewDashboard />
        </div>

        <div v-if="activeTab === 'users'">
          <UserManagement />
        </div>

        <div v-if="activeTab === 'settings'">
          <SiteSettings />
        </div>

        <div v-if="activeTab === 'matchmaking'">
          <MatchmakingQueueAdmin />
        </div>

        <div v-if="activeTab === 'analytics'">
          <UserAnalytics />
        </div>

        <div v-if="activeTab === 'system'">
          <SystemStatus />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import OverviewDashboard from '../components/control/OverviewDashboard.vue'
import UserManagement from '../components/control/UserManagement.vue'
import SiteSettings from '../components/control/SiteSettings.vue'
import UserAnalytics from '../components/control/UserAnalytics.vue'
import MatchmakingQueueAdmin from '../components/control/MatchmakingQueueAdmin.vue'
import SystemStatus from '../components/control/SystemStatus.vue'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref('overview')

const tabs = [
  { id: 'overview', name: 'Overview' },
  { id: 'users', name: 'User Management' },
  { id: 'matchmaking', name: 'Matchmaking' },
  { id: 'analytics', name: 'Analytics' },
  { id: 'settings', name: 'Site Settings' },
  { id: 'system', name: 'System Status' }
]

onMounted(() => {
  // Check if user is staff
  if (!authStore.user?.is_staff) {
    router.push('/')
  }
})
</script>

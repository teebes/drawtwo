<template>
  <div class="control-panel ui-page">
    <div>
      <div class="ui-page-container">
        <!-- Header -->
        <header class="ui-page-header">
          <h1 class="ui-page-title">
            Control Panel
          </h1>
          <p class="ui-page-subtitle">
            Site administration and user management
          </p>
        </header>

        <!-- Navigation Tabs -->
        <div class="ui-tabs-shell">
          <div class="ui-tabs-scroll">
            <nav class="ui-tabs" aria-label="Tabs">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                @click="activeTab = tab.id"
                :class="[
                  'ui-tab',
                  activeTab === tab.id ? 'ui-tab-active' : 'ui-tab-inactive'
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

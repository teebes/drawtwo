<template>
  <div class="system-status">
    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <svg class="h-8 w-8 animate-spin text-primary-600" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span class="ml-3 text-gray-600 dark:text-gray-400">Loading system status...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="rounded-lg bg-red-50 p-6 dark:bg-red-900/30">
      <div class="flex items-center">
        <svg class="h-6 w-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
        </svg>
        <span class="ml-3 text-red-800 dark:text-red-200">{{ error }}</span>
      </div>
      <button @click="fetchStatus" class="mt-4 text-sm text-red-600 hover:text-red-800 dark:text-red-400">
        Retry
      </button>
    </div>

    <!-- Status Content -->
    <div v-else class="space-y-8">
      <!-- Overall Status Banner -->
      <div
        class="rounded-2xl p-6 shadow-sm"
        :class="{
          'bg-green-50 dark:bg-green-900/30': statusData?.status === 'healthy',
          'bg-yellow-50 dark:bg-yellow-900/30': statusData?.status === 'degraded',
          'bg-red-50 dark:bg-red-900/30': statusData?.status === 'error'
        }"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center">
            <div
              class="h-4 w-4 rounded-full"
              :class="{
                'bg-green-500': statusData?.status === 'healthy',
                'bg-yellow-500': statusData?.status === 'degraded',
                'bg-red-500': statusData?.status === 'error'
              }"
            ></div>
            <h2 class="ml-3 font-display text-xl font-semibold" :class="{
              'text-green-800 dark:text-green-200': statusData?.status === 'healthy',
              'text-yellow-800 dark:text-yellow-200': statusData?.status === 'degraded',
              'text-red-800 dark:text-red-200': statusData?.status === 'error'
            }">
              System {{ statusData?.status === 'healthy' ? 'Healthy' : 'Degraded' }}
            </h2>
          </div>
          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-600 dark:text-gray-400">
              Last checked: {{ formatTimestamp(statusData?.timestamp) }}
            </span>
            <button
              @click="fetchStatus"
              :disabled="loading"
              class="rounded-lg bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div class="grid gap-6 lg:grid-cols-2">
        <!-- Service Health Checks -->
        <div class="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-900">
          <h3 class="mb-4 font-display text-lg font-semibold text-gray-900 dark:text-white">
            Service Health
          </h3>
          <div class="space-y-3">
            <!-- Database -->
            <ServiceCheck
              name="Database (PostgreSQL)"
              :status="statusData?.checks?.database?.status"
              :details="statusData?.checks?.database?.message"
            />

            <!-- Redis -->
            <ServiceCheck
              name="Redis"
              :status="statusData?.checks?.redis?.status"
              :details="getRedisDetails()"
            />

            <!-- Celery -->
            <ServiceCheck
              name="Celery Workers"
              :status="statusData?.checks?.celery?.status"
              :details="getCeleryDetails()"
            />
          </div>
        </div>

        <!-- Game Metrics -->
        <div class="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-900">
          <h3 class="mb-4 font-display text-lg font-semibold text-gray-900 dark:text-white">
            Game Metrics
          </h3>
          <div class="space-y-4">
            <MetricRow
              label="Active Games"
              :value="statusData?.metrics?.games?.active ?? '-'"
              description="Games currently in progress"
            />
            <MetricRow
              label="Games Today"
              :value="statusData?.metrics?.games?.today ?? '-'"
              description="Games created today"
            />
            <MetricRow
              label="Pending Effects"
              :value="statusData?.metrics?.games?.with_pending_effects ?? '-'"
              description="Games with queued effects"
              :warning="(statusData?.metrics?.games?.with_pending_effects ?? 0) > 5"
            />
            <MetricRow
              label="Matchmaking Queue"
              :value="statusData?.metrics?.matchmaking?.queued_players ?? '-'"
              description="Players waiting for match"
            />
          </div>
        </div>
      </div>

      <!-- Redis Details (expanded) -->
      <div v-if="statusData?.checks?.redis?.status === 'ok'" class="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-900">
        <h3 class="mb-4 font-display text-lg font-semibold text-gray-900 dark:text-white">
          Redis Details
        </h3>
        <div class="grid gap-4 sm:grid-cols-3">
          <div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
            <div class="text-sm text-gray-500 dark:text-gray-400">Connected Clients</div>
            <div class="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
              {{ statusData?.checks?.redis?.connected_clients ?? '-' }}
            </div>
          </div>
          <div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
            <div class="text-sm text-gray-500 dark:text-gray-400">Memory Usage</div>
            <div class="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
              {{ statusData?.checks?.redis?.used_memory_human ?? '-' }}
            </div>
          </div>
          <div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
            <div class="text-sm text-gray-500 dark:text-gray-400">Uptime</div>
            <div class="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
              {{ formatUptime(statusData?.checks?.redis?.uptime_in_seconds) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Celery Worker Details -->
      <div v-if="statusData?.checks?.celery?.workers" class="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-900">
        <h3 class="mb-4 font-display text-lg font-semibold text-gray-900 dark:text-white">
          Celery Workers
        </h3>
        <div class="space-y-2">
          <div
            v-for="(info, workerName) in statusData?.checks?.celery?.workers"
            :key="workerName"
            class="flex items-center justify-between rounded-lg bg-gray-50 p-3 dark:bg-gray-800"
          >
            <div class="flex items-center">
              <div class="h-2 w-2 rounded-full bg-green-500"></div>
              <span class="ml-3 font-mono text-sm text-gray-900 dark:text-white">{{ workerName }}</span>
            </div>
            <span class="text-sm text-gray-500 dark:text-gray-400">
              {{ info.active_tasks }} active task(s)
            </span>
          </div>
        </div>
      </div>

      <!-- Troubleshooting Guide -->
      <div v-if="statusData?.status === 'degraded'" class="rounded-2xl border border-yellow-200 bg-yellow-50 p-6 dark:border-yellow-700 dark:bg-yellow-900/30">
        <h3 class="mb-3 font-display text-lg font-semibold text-yellow-800 dark:text-yellow-200">
          Troubleshooting
        </h3>
        <ul class="space-y-2 text-sm text-yellow-700 dark:text-yellow-300">
          <li v-if="statusData?.checks?.database?.status !== 'ok'" class="flex items-start">
            <span class="mr-2">•</span>
            <span><strong>Database:</strong> Check PostgreSQL container is running. Try: <code class="rounded bg-yellow-100 px-1 dark:bg-yellow-800">docker compose logs db</code></span>
          </li>
          <li v-if="statusData?.checks?.redis?.status !== 'ok'" class="flex items-start">
            <span class="mr-2">•</span>
            <span><strong>Redis:</strong> Check Redis container is running. Try: <code class="rounded bg-yellow-100 px-1 dark:bg-yellow-800">docker compose logs redis</code></span>
          </li>
          <li v-if="statusData?.checks?.celery?.status !== 'ok'" class="flex items-start">
            <span class="mr-2">•</span>
            <span><strong>Celery:</strong> Check Celery worker is running. Try: <code class="rounded bg-yellow-100 px-1 dark:bg-yellow-800">docker compose logs celery-worker</code></span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import api from '../../config/api'

// Sub-components defined inline for simplicity
const ServiceCheck = {
  props: ['name', 'status', 'details'],
  template: `
    <div class="flex items-center justify-between rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
      <div class="flex items-center">
        <div
          class="h-2.5 w-2.5 rounded-full"
          :class="{
            'bg-green-500': status === 'ok',
            'bg-yellow-500': status === 'warning',
            'bg-red-500': status === 'error',
            'bg-gray-400': !status
          }"
        ></div>
        <span class="ml-3 font-medium text-gray-900 dark:text-white">{{ name }}</span>
      </div>
      <div class="flex items-center">
        <span
          v-if="details"
          class="mr-2 text-xs text-gray-500 dark:text-gray-400"
        >{{ details }}</span>
        <span
          class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
          :class="{
            'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200': status === 'ok',
            'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200': status === 'warning',
            'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200': status === 'error',
            'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200': !status
          }"
        >
          {{ status === 'ok' ? 'Healthy' : status === 'warning' ? 'Warning' : status === 'error' ? 'Error' : 'Unknown' }}
        </span>
      </div>
    </div>
  `
}

const MetricRow = {
  props: ['label', 'value', 'description', 'warning'],
  template: `
    <div class="flex items-center justify-between">
      <div>
        <div class="font-medium text-gray-900 dark:text-white">{{ label }}</div>
        <div class="text-sm text-gray-500 dark:text-gray-400">{{ description }}</div>
      </div>
      <div
        class="text-2xl font-semibold"
        :class="warning ? 'text-yellow-600 dark:text-yellow-400' : 'text-gray-900 dark:text-white'"
      >
        {{ value }}
      </div>
    </div>
  `
}

interface SystemStatusData {
  status: 'healthy' | 'degraded' | 'error'
  checks: {
    database: { status: string; message?: string }
    redis: {
      status: string
      message?: string
      connected_clients?: number
      used_memory_human?: string
      uptime_in_seconds?: number
    }
    celery: {
      status: string
      message?: string
      worker_count?: number
      workers?: Record<string, { active_tasks: number }>
    }
  }
  metrics: {
    games: {
      active: number
      today: number
      with_pending_effects: number
    }
    matchmaking: {
      queued_players: number
    }
  }
  timestamp: string
}

const loading = ref(true)
const error = ref<string | null>(null)
const statusData = ref<SystemStatusData | null>(null)
let refreshInterval: ReturnType<typeof setInterval> | null = null

const fetchStatus = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await api.get('/control/system-status/')
    statusData.value = response.data
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || 'Failed to fetch system status'
  } finally {
    loading.value = false
  }
}

const getRedisDetails = () => {
  const redis = statusData.value?.checks?.redis
  if (redis?.status === 'error') return redis.message
  if (redis?.connected_clients !== undefined) {
    return `${redis.connected_clients} clients`
  }
  return undefined
}

const getCeleryDetails = () => {
  const celery = statusData.value?.checks?.celery
  if (celery?.status === 'error') return celery.message
  if (celery?.status === 'warning') return celery.message
  if (celery?.worker_count !== undefined) {
    return `${celery.worker_count} worker(s)`
  }
  return undefined
}

const formatTimestamp = (timestamp: string | undefined) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleTimeString()
}

const formatUptime = (seconds: number | undefined) => {
  if (!seconds) return '-'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  if (days > 0) return `${days}d ${hours}h`
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

onMounted(() => {
  fetchStatus()
  // Auto-refresh every 30 seconds
  refreshInterval = setInterval(fetchStatus, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

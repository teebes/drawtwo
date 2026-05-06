<template>
  <div class="site-settings">
    <div v-if="loading" class="text-center py-8">
      <div class="text-gray-600 dark:text-gray-300">Loading...</div>
    </div>

    <div v-else>
      <Panel title="Site Access Controls">
        <form @submit.prevent="updateSettings" class="space-y-6">
          <!-- Whitelist Mode -->
          <div class="flex items-start">
            <div class="flex items-center h-5">
              <input
                id="whitelist-mode"
                v-model="formData.whitelist_mode_enabled"
                type="checkbox"
                class="ui-checkbox"
              />
            </div>
            <div class="ml-3">
              <label for="whitelist-mode" class="text-sm font-medium text-gray-900 dark:text-white">
                Enable Whitelist Mode
              </label>
              <p class="text-sm text-gray-600 dark:text-gray-400">
                When enabled, only approved users can log in and access the site.
                Staff users are always allowed.
              </p>
            </div>
          </div>

          <!-- Signup Disabled -->
          <div class="flex items-start">
            <div class="flex items-center h-5">
              <input
                id="signup-disabled"
                v-model="formData.signup_disabled"
                type="checkbox"
                class="ui-checkbox"
              />
            </div>
            <div class="ml-3">
              <label for="signup-disabled" class="text-sm font-medium text-gray-900 dark:text-white">
                Disable New Signups
              </label>
              <p class="text-sm text-gray-600 dark:text-gray-400">
                When enabled, new user registrations will be completely disabled.
              </p>
            </div>
          </div>

          <!-- Error Display -->
          <div v-if="error" class="ui-alert ui-alert-error">
            {{ error }}
          </div>

          <!-- Success Display -->
          <div v-if="successMessage" class="ui-alert ui-alert-success">
            {{ successMessage }}
          </div>

          <!-- Submit Button -->
          <div class="flex justify-end">
            <GameButton
              type="submit"
              variant="primary"
              :disabled="saving"
            >
              {{ saving ? 'Saving...' : 'Save Settings' }}
            </GameButton>
          </div>
        </form>
      </Panel>

      <!-- Current Status Panel -->
      <div class="mt-8">
        <Panel title="Current Status" class="space-y-4">
          <div class="grid gap-4 md:grid-cols-2">
            <div class="ui-panel-muted">
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium text-gray-900 dark:text-white">
                  Whitelist Mode
                </span>
                <span
                  :class="[
                    'ui-status-badge',
                    settings?.whitelist_mode_enabled
                      ? 'ui-status-danger'
                      : 'ui-status-success'
                  ]"
                >
                  {{ settings?.whitelist_mode_enabled ? 'ENABLED' : 'DISABLED' }}
                </span>
              </div>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
                {{ settings?.whitelist_mode_enabled
                  ? 'Only approved users can access the site'
                  : 'All verified users can access the site' }}
              </p>
            </div>

            <div class="ui-panel-muted">
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium text-gray-900 dark:text-white">
                  User Signups
                </span>
                <span
                  :class="[
                    'ui-status-badge',
                    settings?.signup_disabled
                      ? 'ui-status-danger'
                      : 'ui-status-success'
                  ]"
                >
                  {{ settings?.signup_disabled ? 'DISABLED' : 'ENABLED' }}
                </span>
              </div>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
                {{ settings?.signup_disabled
                  ? 'New user registrations are blocked'
                  : 'New users can register accounts' }}
              </p>
            </div>
          </div>

          <div v-if="settings?.updated_at" class="text-xs text-gray-500 dark:text-gray-400">
            Last updated: {{ formatDate(settings.updated_at) }}
          </div>
        </Panel>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from '../../config/api'
import Panel from '../layout/Panel.vue'
import GameButton from '../ui/GameButton.vue'
import type { SiteSettings } from '../../types/control'

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const settings = ref<SiteSettings | null>(null)

const formData = reactive({
  whitelist_mode_enabled: false,
  signup_disabled: false
})

const fetchSettings = async () => {
  try {
    loading.value = true
    error.value = null

    const response = await axios.get('/control/settings/')
    settings.value = response.data

    // Update form data
    formData.whitelist_mode_enabled = response.data.whitelist_mode_enabled
    formData.signup_disabled = response.data.signup_disabled
  } catch (err: any) {
    error.value = err.response?.data?.error || 'Failed to load settings'
  } finally {
    loading.value = false
  }
}

const updateSettings = async () => {
  try {
    saving.value = true
    error.value = null
    successMessage.value = null

    const response = await axios.patch('/control/settings/', formData)
    settings.value = response.data
    successMessage.value = 'Settings updated successfully!'

    // Clear success message after 3 seconds
    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  } catch (err: any) {
    error.value = err.response?.data?.error || 'Failed to update settings'
  } finally {
    saving.value = false
  }
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  fetchSettings()
})
</script>

<style scoped>
.site-settings {
  /* Custom styles if needed */
}
</style>

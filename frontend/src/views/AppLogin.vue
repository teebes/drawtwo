<template>
  <div class="ui-page">
    <main class="ui-page-container ui-page-container-narrow flex min-h-screen items-center">
      <section class="mx-auto w-full max-w-md">
        <div class="mb-6 flex items-center justify-center gap-3">
          <img
            src="/drawtwo_logo.png"
            alt="DrawTwo Logo"
            class="h-10 w-10 rounded-lg object-contain"
          />
          <h1 class="font-display text-3xl font-bold text-gray-900 dark:text-white">
            DrawTwo
          </h1>
        </div>

        <div class="ui-panel gap-5">
          <div>
            <h2 class="ui-panel-title text-2xl">Open Login Link</h2>
            <p class="ui-panel-subtitle">
              Use the app when it is installed, or continue here in the browser.
            </p>
          </div>

          <div v-if="message" :class="['ui-alert', messageClass]">
            {{ message }}
          </div>

          <a :href="appUrl" class="ui-btn ui-btn-lg ui-btn-primary w-full">
            <LogIn class="h-5 w-5" aria-hidden="true" />
            Open DrawTwo App
          </a>

          <button
            type="button"
            class="ui-btn ui-btn-lg ui-btn-secondary w-full"
            @click="copyCode"
          >
            <Copy class="h-5 w-5" aria-hidden="true" />
            Copy Confirmation Code
          </button>

          <button
            type="button"
            class="ui-btn ui-btn-lg ui-btn-outline w-full"
            :disabled="authStore.loading"
            @click="continueInBrowser"
          >
            <ExternalLink class="h-5 w-5" aria-hidden="true" />
            {{ authStore.loading ? 'Signing in...' : 'Continue in Browser' }}
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Copy, ExternalLink, LogIn } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const key = computed(() => String(route.params.key || ''))
const appUrl = computed(() => `drawtwo://login/${encodeURIComponent(key.value)}`)
const messageClass = computed(() =>
  messageType.value === 'success' ? 'ui-alert-success' : 'ui-alert-error'
)

const showMessage = (text: string, type: 'success' | 'error') => {
  message.value = text
  messageType.value = type
}

const copyCode = async () => {
  try {
    await navigator.clipboard.writeText(key.value)
    showMessage('Confirmation code copied.', 'success')
  } catch {
    showMessage('Copy failed. Select and copy the code from the email instead.', 'error')
  }
}

const continueInBrowser = async () => {
  const result = await authStore.confirmEmail(key.value)

  if (result.success) {
    router.push('/play')
    return
  }

  const errorMessage = result.error?.error
    || result.error?.message
    || 'The login link is invalid or expired.'
  showMessage(errorMessage, 'error')
}
</script>

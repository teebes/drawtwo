<template>
  <div class="fixed top-20 right-4 z-50 space-y-2">
    <transition-group
      name="toast"
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="transform translate-x-full opacity-0"
      enter-to-class="transform translate-x-0 opacity-100"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="transform translate-x-0 opacity-100"
      leave-to-class="transform translate-x-full opacity-0"
      tag="div"
    >
      <div
        v-for="notification in notificationStore.activeNotifications"
        :key="notification.id"
        class="toast-notification max-w-sm w-full bg-white rounded-lg shadow-lg border-l-4 p-4 dark:bg-gray-800"
        :class="toastClasses(notification.type)"
      >
        <div class="flex items-start">
          <!-- Icon -->
          <div class="flex-shrink-0">
            <svg
              v-if="notification.type === 'success'"
              class="h-5 w-5 text-green-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            <svg
              v-else-if="notification.type === 'error'"
              class="h-5 w-5 text-red-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
            <svg
              v-else-if="notification.type === 'warning'"
              class="h-5 w-5 text-yellow-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
            </svg>
            <svg
              v-else
              class="h-5 w-5 text-blue-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </div>

          <!-- Content -->
          <div class="ml-3 flex-1">
            <h4 v-if="notification.title" class="text-sm font-medium" :class="titleClasses(notification.type)">
              {{ notification.title }}
            </h4>
            <p class="text-sm" :class="messageClasses(notification.type)">
              {{ notification.message }}
            </p>
          </div>

          <!-- Close button -->
          <div class="ml-4 flex-shrink-0">
            <button
              @click="notificationStore.dismissNotification(notification.id)"
              class="inline-flex text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none focus:text-gray-600 dark:focus:text-gray-300 transition-colors"
            >
              <span class="sr-only">Close</span>
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { useNotificationStore } from '../../stores/notifications'

const notificationStore = useNotificationStore()

const toastClasses = (type) => {
  const classMap = {
    success: 'border-green-400 bg-green-50 dark:bg-green-900/80',
    error: 'border-red-400 bg-red-50 dark:bg-red-900/80',
    warning: 'border-yellow-400 bg-yellow-50 dark:bg-yellow-900/80',
    info: 'border-blue-400 bg-blue-50 dark:bg-blue-900/80'
  }
  return classMap[type] || classMap.info
}

const titleClasses = (type) => {
  const classMap = {
    success: 'text-green-800 dark:text-green-200',
    error: 'text-red-800 dark:text-red-200',
    warning: 'text-yellow-800 dark:text-yellow-200',
    info: 'text-blue-800 dark:text-blue-200'
  }
  return classMap[type] || classMap.info
}

const messageClasses = (type) => {
  const classMap = {
    success: 'text-green-700 dark:text-green-300',
    error: 'text-red-700 dark:text-red-300',
    warning: 'text-yellow-700 dark:text-yellow-300',
    info: 'text-blue-700 dark:text-blue-300'
  }
  return classMap[type] || classMap.info
}
</script>

<style scoped>
.toast-notification {
  max-width: 384px; /* max-w-sm */
}

/* Toast animations */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
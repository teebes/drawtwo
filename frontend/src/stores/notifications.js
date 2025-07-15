import { defineStore } from 'pinia'

export const useNotificationStore = defineStore('notifications', {
  state: () => ({
    notifications: []
  }),

  getters: {
    activeNotifications: (state) => state.notifications.filter(n => !n.dismissed)
  },

  actions: {
    addNotification(notification) {
      const id = Date.now() + Math.random()
      const newNotification = {
        id,
        type: notification.type || 'info', // 'success', 'error', 'warning', 'info'
        title: notification.title || '',
        message: notification.message || '',
        duration: notification.duration || 5000, // Auto-dismiss after 5 seconds by default
        persistent: notification.persistent || false, // If true, won't auto-dismiss
        dismissed: false,
        timestamp: new Date()
      }

      this.notifications.push(newNotification)

      // Auto-dismiss if not persistent
      if (!newNotification.persistent && newNotification.duration > 0) {
        setTimeout(() => {
          this.dismissNotification(id)
        }, newNotification.duration)
      }

      return id
    },

    dismissNotification(id) {
      const notification = this.notifications.find(n => n.id === id)
      if (notification) {
        notification.dismissed = true
      }
    },

    clearAll() {
      this.notifications.forEach(n => n.dismissed = true)
    },

    // Convenience methods for different notification types
    success(message, options = {}) {
      return this.addNotification({
        type: 'success',
        message,
        ...options
      })
    },

    error(message, options = {}) {
      return this.addNotification({
        type: 'error',
        message,
        duration: 8000, // Errors stay longer by default
        ...options
      })
    },

    warning(message, options = {}) {
      return this.addNotification({
        type: 'warning',
        message,
        ...options
      })
    },

    info(message, options = {}) {
      return this.addNotification({
        type: 'info',
        message,
        ...options
      })
    },

    // Handle API errors automatically
    handleApiError(error, customMessage = null) {
      let message = customMessage

      if (!message) {
        if (error.response?.data?.error) {
          message = error.response.data.error
        } else if (error.response?.data?.message) {
          message = error.response.data.message
        } else if (error.message) {
          message = error.message
        } else {
          message = 'An unexpected error occurred'
        }
      }

      return this.error(message)
    },

    // Handle API success responses
    handleApiSuccess(response, customMessage = null) {
      let message = customMessage

      if (!message) {
        if (response.data?.message) {
          message = response.data.message
        } else {
          message = 'Operation completed successfully'
        }
      }

      return this.success(message)
    }
  }
})
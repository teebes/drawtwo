import { defineStore } from 'pinia'
import { AxiosError, AxiosResponse } from 'axios'

// Types for notifications
type NotificationType = 'success' | 'error' | 'warning' | 'info'

interface Notification {
  id: number
  type: NotificationType
  title: string
  message: string
  duration: number
  persistent: boolean
  dismissed: boolean
  timestamp: Date
}

interface NotificationOptions {
  type?: NotificationType
  title?: string
  message?: string
  duration?: number
  persistent?: boolean
}

interface NotificationState {
  notifications: Notification[]
}

export const useNotificationStore = defineStore('notifications', {
  state: (): NotificationState => ({
    notifications: []
  }),

  getters: {
    activeNotifications: (state): Notification[] => state.notifications.filter(n => !n.dismissed)
  },

  actions: {
    addNotification(notification: NotificationOptions): number {
      const id = Date.now() + Math.random()
      const newNotification: Notification = {
        id,
        type: notification.type || 'info',
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

    dismissNotification(id: number): void {
      const notification = this.notifications.find(n => n.id === id)
      if (notification) {
        notification.dismissed = true
      }
    },

    clearAll(): void {
      this.notifications.forEach(n => n.dismissed = true)
    },

    // Convenience methods for different notification types
    success(message: string, options: Omit<NotificationOptions, 'type' | 'message'> = {}): number {
      return this.addNotification({
        type: 'success',
        message,
        ...options
      })
    },

    error(message: string, options: Omit<NotificationOptions, 'type' | 'message'> = {}): number {
      return this.addNotification({
        type: 'error',
        message,
        duration: 8000, // Errors stay longer by default
        ...options
      })
    },

    warning(message: string, options: Omit<NotificationOptions, 'type' | 'message'> = {}): number {
      return this.addNotification({
        type: 'warning',
        message,
        ...options
      })
    },

    info(message: string, options: Omit<NotificationOptions, 'type' | 'message'> = {}): number {
      return this.addNotification({
        type: 'info',
        message,
        ...options
      })
    },

    // Handle API errors automatically
    handleApiError(error: AxiosError | Error, customMessage: string | null = null): number {
      let message = customMessage

      if (!message) {
        if ('response' in error && error.response?.data) {
          const data = error.response.data as any
          if (data.error) {
            message = data.error
          } else if (data.message) {
            message = data.message
          } else if (error.message) {
            message = error.message
          } else {
            message = 'An unexpected error occurred'
          }
        } else if (error.message) {
          message = error.message
        } else {
          message = 'An unexpected error occurred'
        }
      }

      return this.error(message)
    },

    // Handle API success responses
    handleApiSuccess(response: AxiosResponse, customMessage: string | null = null): number {
      let message = customMessage

      if (!message) {
        const data = response.data as any
        if (data?.message) {
          message = data.message
        } else {
          message = 'Operation completed successfully'
        }
      }

      return this.success(message)
    }
  }
})

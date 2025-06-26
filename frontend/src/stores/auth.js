import { defineStore } from 'pinia'
import axios from '../config/api.js'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    loading: false,
    error: null
  }),

  actions: {
    // Initialize authentication state from localStorage
    initAuth() {
      const accessToken = localStorage.getItem('accessToken')
      const refreshToken = localStorage.getItem('refreshToken')
      const userData = localStorage.getItem('userData')

      if (accessToken && refreshToken && userData) {
        this.accessToken = accessToken
        this.refreshToken = refreshToken
        this.user = JSON.parse(userData)
        this.isAuthenticated = true

        // Set axios authorization header
        axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
      }
    },

    // Store tokens and user data
    setAuthData(accessToken, refreshToken, user) {
      this.accessToken = accessToken
      this.refreshToken = refreshToken
      this.user = user
      this.isAuthenticated = true

      // Store in localStorage
      localStorage.setItem('accessToken', accessToken)
      localStorage.setItem('refreshToken', refreshToken)
      localStorage.setItem('userData', JSON.stringify(user))

      // Set axios authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
    },

    // Clear authentication data
    clearAuth() {
      this.user = null
      this.accessToken = null
      this.refreshToken = null
      this.isAuthenticated = false

      // Clear localStorage
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('userData')

      // Clear axios authorization header
      delete axios.defaults.headers.common['Authorization']
    },

    // Register a new user (passwordless)
    async register(userData) {
      this.loading = true
      this.error = null

      try {
        const response = await axios.post('/auth/register/', userData)
        this.loading = false
        return { success: true, data: response.data }
      } catch (error) {
        this.loading = false
        this.error = error.response?.data || { message: 'Registration failed' }
        return { success: false, error: this.error }
      }
    },

    // Send passwordless login email
    async sendLoginEmail(email) {
      this.loading = true
      this.error = null

      try {
        const response = await axios.post('/auth/passwordless-login/', { email })
        this.loading = false
        return { success: true, data: response.data }
      } catch (error) {
        this.loading = false
        this.error = error.response?.data || { message: 'Login email failed' }
        return { success: false, error: this.error }
      }
    },

    // Confirm email and login
    async confirmEmail(key) {
      this.loading = true
      this.error = null

      try {
        const response = await axios.post('/auth/email-confirm/', { key })

        if (response.data.access && response.data.refresh && response.data.user) {
          this.setAuthData(response.data.access, response.data.refresh, response.data.user)
        }

        this.loading = false
        return { success: true, data: response.data }
      } catch (error) {
        this.loading = false
        this.error = error.response?.data || { message: 'Email confirmation failed' }
        return { success: false, error: this.error }
      }
    },

    // Google OAuth login
    async googleLogin(accessToken) {
      this.loading = true
      this.error = null

      try {
        const response = await axios.post('/auth/google/', { access_token: accessToken })

        if (response.data.access_token && response.data.refresh_token && response.data.user) {
          this.setAuthData(response.data.access_token, response.data.refresh_token, response.data.user)
        }

        this.loading = false
        return { success: true, data: response.data }
      } catch (error) {
        this.loading = false
        this.error = error.response?.data || { message: 'Google login failed' }
        return { success: false, error: this.error }
      }
    },

    // Logout
    async logout() {
      this.loading = true

      try {
        // Call logout endpoint if authenticated
        if (this.isAuthenticated) {
          // Create a custom axios instance to avoid the interceptor
          const logoutAxios = axios.create()
          logoutAxios.defaults.headers.common['Authorization'] = `Bearer ${this.accessToken}`
          await logoutAxios.post('/auth/auth/logout/')
        }
      } catch (error) {
        console.error('Logout API call failed:', error)
        // Don't worry if logout fails - clear local auth anyway
      } finally {
        this.clearAuth()
        this.loading = false
      }
    },

    // Refresh access token
    async refreshAccessToken() {
      if (!this.refreshToken) {
        this.clearAuth()
        return false
      }

      try {
        // Use a clean axios instance to avoid interceptor loops
        const refreshAxios = axios.create({
          baseURL: axios.defaults.baseURL
        })

        const response = await refreshAxios.post('/auth/token/refresh/', {
          refresh: this.refreshToken
        })

        this.accessToken = response.data.access
        localStorage.setItem('accessToken', response.data.access)
        axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access}`

        return true
      } catch (error) {
        console.error('Token refresh failed:', error)
        this.clearAuth()
        return false
      }
    },

    // Get current user profile
    async getCurrentUser() {
      if (!this.isAuthenticated) return null

      try {
        const response = await axios.get('/auth/profile/')
        this.user = response.data
        localStorage.setItem('userData', JSON.stringify(response.data))
        return response.data
      } catch (error) {
        console.error('Get current user failed:', error)
        // If unauthorized, try to refresh token
        if (error.response?.status === 401) {
          const refreshed = await this.refreshAccessToken()
          if (refreshed) {
            // Retry the request
            try {
              const response = await axios.get('/auth/profile/')
              this.user = response.data
              localStorage.setItem('userData', JSON.stringify(response.data))
              return response.data
            } catch (retryError) {
              console.error('Retry get current user failed:', retryError)
              this.clearAuth()
            }
          }
        }
        return null
      }
    },

    // Test protected endpoint
    async testProtectedEndpoint() {
      try {
        const response = await axios.get('/auth/test/')
        return { success: true, data: response.data }
      } catch (error) {
        // If unauthorized, try to refresh token
        if (error.response?.status === 401) {
          const refreshed = await this.refreshAccessToken()
          if (refreshed) {
            // Retry the request
            try {
              const response = await axios.get('/auth/test/')
              return { success: true, data: response.data }
            } catch (retryError) {
              return { success: false, error: retryError.response?.data || { message: 'Test failed' } }
            }
          }
        }
        return { success: false, error: error.response?.data || { message: 'Test failed' } }
      }
    }
  }
})
import { defineStore } from 'pinia'
import axios, { getBaseUrl } from '../config/api'

// Types for API responses
interface User {
  id: number
  email: string
  username?: string
  first_name?: string
  last_name?: string
  is_active: boolean
  date_joined: string
  [key: string]: any // Allow for additional user fields
}

interface AuthTokenResponse {
  access: string
  refresh: string
  user: User
}

interface GoogleAuthResponse {
  access_token: string
  refresh_token: string
  user: User
}

interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: {
    message: string
    [key: string]: any
  }
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  loading: boolean
  error: any | null
  userSocket: WebSocket | null
  userWsStatus: 'disconnected' | 'connecting' | 'connected'
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    loading: false,
    error: null,
    userSocket: null,
    userWsStatus: 'disconnected'
  }),

  actions: {
    // Initialize authentication state from localStorage
    initAuth(): void {
      const accessToken = localStorage.getItem('accessToken')
      const refreshToken = localStorage.getItem('refreshToken')
      const userData = localStorage.getItem('userData')

      if (accessToken && refreshToken && userData) {
        this.accessToken = accessToken
        this.refreshToken = refreshToken
        this.user = JSON.parse(userData) as User
        this.isAuthenticated = true

        // Set axios authorization header
        axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
      }
    },

    // Store tokens and user data
    setAuthData(accessToken: string, refreshToken: string, user: User): void {
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
    clearAuth(): void {
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
    async register(userData: Record<string, any>): Promise<ApiResponse> {
      this.loading = true
      this.error = null

      try {
        const response = await axios.post('/auth/register/', userData)
        this.loading = false
        return { success: true, data: response.data }
      } catch (error: any) {
        this.loading = false
        this.error = error.response?.data || { message: 'Registration failed' }
        return { success: false, error: this.error }
      }
    },

    // Send passwordless login email
    async sendLoginEmail(email: string): Promise<ApiResponse> {
      this.loading = true
      this.error = null

      try {
        const response = await axios.post('/auth/passwordless-login/', { email })
        this.loading = false
        return { success: true, data: response.data }
      } catch (error: any) {
        this.loading = false
        this.error = error.response?.data || { message: 'Login email failed' }
        return { success: false, error: this.error }
      }
    },

    // Confirm email and login
    async confirmEmail(key: string): Promise<ApiResponse> {
      this.loading = true
      this.error = null

      try {
        const response = await axios.post('/auth/email-confirm/', { key })

        if (response.data.access && response.data.refresh && response.data.user) {
          this.setAuthData(response.data.access, response.data.refresh, response.data.user)
        }

        this.loading = false
        return { success: true, data: response.data }
      } catch (error: any) {
        this.loading = false
        this.error = error.response?.data || { message: 'Email confirmation failed' }
        return { success: false, error: this.error }
      }
    },

    // Google OAuth login
    async googleLogin(accessToken: string): Promise<ApiResponse> {
      this.loading = true
      this.error = null

      try {
        const response = await axios.post('/auth/google/', { access_token: accessToken })

        // dj-rest-auth returns 'access' and 'refresh', not 'access_token' and 'refresh_token'
        const access = response.data.access_token || response.data.access
        const refresh = response.data.refresh_token || response.data.refresh
        const user = response.data.user

        if (access && refresh && user) {
          this.setAuthData(access, refresh, user)
        }

        this.loading = false
        return { success: true, data: response.data }
      } catch (error: any) {
        this.loading = false
        this.error = error.response?.data || { message: 'Google login failed' }
        return { success: false, error: this.error }
      }
    },

    // Logout
    async logout(): Promise<void> {
      this.loading = true

      try {
        // Call logout endpoint if authenticated
        if (this.isAuthenticated) {
          // Create a custom axios instance to avoid the interceptor
          const logoutAxios = axios.create()
          logoutAxios.defaults.headers.common['Authorization'] = `Bearer ${this.accessToken}`
          await logoutAxios.post('/auth/auth/logout/')
        }
      } catch (error: any) {
        console.error('Logout API call failed:', error)
        // Don't worry if logout fails - clear local auth anyway
      } finally {
        this.clearAuth()
        this.loading = false
      }
    },

    // Refresh access token
    async refreshAccessToken(): Promise<boolean> {
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

        // Update access token
        this.accessToken = response.data.access
        localStorage.setItem('accessToken', response.data.access)
        axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access}`

        // Update refresh token if a new one is provided (token rotation)
        if (response.data.refresh) {
          this.refreshToken = response.data.refresh
          localStorage.setItem('refreshToken', response.data.refresh)
        }

        return true
      } catch (error: any) {
        console.error('Token refresh failed:', error)
        this.clearAuth()
        return false
      }
    },

    // Get current user profile
    async getCurrentUser(): Promise<User | null> {
      if (!this.isAuthenticated) return null

      try {
        const response = await axios.get('/auth/profile/')
        this.user = response.data as User
        localStorage.setItem('userData', JSON.stringify(response.data))
        return response.data
      } catch (error: any) {
        console.error('Get current user failed:', error)
        // If unauthorized, try to refresh token
        if (error.response?.status === 401) {
          const refreshed = await this.refreshAccessToken()
          if (refreshed) {
            // Retry the request
            try {
              const response = await axios.get('/auth/profile/')
              this.user = response.data as User
              localStorage.setItem('userData', JSON.stringify(response.data))
              return response.data
            } catch (retryError: any) {
              console.error('Retry get current user failed:', retryError)
              this.clearAuth()
            }
          }
        }
        return null
      }
    },

    // Update user profile
    async updateProfile(data: Partial<User>): Promise<ApiResponse> {
      this.loading = true
      this.error = null

      try {
        const response = await axios.patch('/auth/profile/', data)
        this.user = response.data as User
        localStorage.setItem('userData', JSON.stringify(response.data))
        this.loading = false
        return { success: true, data: response.data }
      } catch (error: any) {
        this.loading = false
        this.error = error.response?.data || { message: 'Update profile failed' }
        return { success: false, error: this.error }
      }
    },

    // Test protected endpoint
    async testProtectedEndpoint(): Promise<ApiResponse> {
      try {
        const response = await axios.get('/auth/test/')
        return { success: true, data: response.data }
      } catch (error: any) {
        // If unauthorized, try to refresh token
        if (error.response?.status === 401) {
          const refreshed = await this.refreshAccessToken()
          if (refreshed) {
            // Retry the request
            try {
              const response = await axios.get('/auth/test/')
              return { success: true, data: response.data }
            } catch (retryError: any) {
              return { success: false, error: retryError.response?.data || { message: 'Test failed' } }
            }
          }
        }
        return { success: false, error: error.response?.data || { message: 'Test failed' } }
      }
    },

    // Connect to user websocket for real-time notifications
    connectUserWebSocket(): void {
      if (!this.isAuthenticated || !this.accessToken) {
        console.warn('Cannot connect user websocket: not authenticated')
        return
      }

      if (this.userSocket && this.userWsStatus === 'connected') {
        console.log('User websocket already connected')
        return
      }

      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = new URL('/ws/user/', getBaseUrl())
      wsUrl.protocol = wsProtocol
      wsUrl.searchParams.set('token', this.accessToken)

      this.userWsStatus = 'connecting'
      this.userSocket = new WebSocket(wsUrl.toString())

      this.userSocket.onopen = () => {
        console.log('User websocket connected')
        this.userWsStatus = 'connected'
      }

      this.userSocket.onmessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data)
        this.handleUserWebSocketMessage(data)
      }

      this.userSocket.onerror = (error: Event) => {
        console.error('User websocket error:', error)
      }

      this.userSocket.onclose = () => {
        console.log('User websocket disconnected')
        this.userWsStatus = 'disconnected'
      }
    },

    // Disconnect user websocket
    disconnectUserWebSocket(): void {
      if (this.userSocket) {
        this.userSocket.close()
        this.userSocket = null
        this.userWsStatus = 'disconnected'
      }
    },

    // Handle user websocket messages
    handleUserWebSocketMessage(data: any): void {
      console.log('User websocket message:', data)

      if (data.type === 'matchmaking_success') {
        // Navigate to the game board
        const router = (window as any).vueRouter
        if (router) {
          router.push({
            name: 'Board',
            params: {
              slug: data.title_slug,
              game_id: data.game_id
            }
          })
        }
      }
    }
  }
})

import axios from 'axios'

// API Configuration - Use runtime hostname detection
const getApiBaseUrl = () => {
  // Check for explicit environment configuration first
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }

  // If we're in development mode (localhost), use the dev server
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000/api'
  }
  // In production, use relative path (same domain)
  return '/api'
}

// Get the base URL without the /api suffix - useful for WebSocket connections
export const getBaseUrl = () => {
  // Check for explicit environment configuration first
  if (import.meta.env.VITE_BASE_URL) {
    return import.meta.env.VITE_BASE_URL
  }

  const hostname = window.location.hostname
  const isDev = hostname === 'localhost' || hostname === '127.0.0.1' || hostname.includes('localhost')

  // Debug logging to help identify the issue
  console.log('getBaseUrl debug:', {
    hostname,
    origin: window.location.origin,
    isDev,
    href: window.location.href
  })

  // If we're in development mode (localhost), use the dev server
  if (isDev) {
    return 'http://localhost:8000'
  }

  // In production, use current domain
  // For drawtwo.com, this should return https://drawtwo.com
  return window.location.origin
}

const API_BASE_URL = getApiBaseUrl()

// Configure axios defaults
axios.defaults.baseURL = API_BASE_URL
// Note: withCredentials is set per-request basis to avoid CSRF issues with auth endpoints

// Setup axios interceptor for automatic token refresh
// Note: This will be initialized after the auth store is available
let authStore = null
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })

  failedQueue = []
}

export const initializeAuthInterceptor = (store) => {
  authStore = store

  axios.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config

      // Don't try to refresh for these conditions:
      // 1. Not a 401 error
      // 2. No refresh token available
      // 3. Request is to the refresh endpoint itself (prevent infinite loop!)
      if (
        error.response?.status !== 401 ||
        !authStore?.refreshToken ||
        originalRequest.url?.includes('/auth/token/refresh/')
      ) {
        // If it's a 401 and we can't refresh, clear auth and redirect
        if (error.response?.status === 401 && authStore && !originalRequest.url?.includes('/auth/token/refresh/')) {
          authStore.clearAuth()
          // Redirect to login (avoid redirecting if already on login page)
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
        }
        return Promise.reject(error)
      }

      // If we've already retried this request, don't retry again
      if (originalRequest._retry) {
        return Promise.reject(error)
      }

      // If token refresh is already in progress, queue this request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest._retry = true
          originalRequest.headers['Authorization'] = `Bearer ${token}`
          return axios.request(originalRequest)
        }).catch(err => {
          return Promise.reject(err)
        })
      }

      // Mark this request as already attempted
      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshed = await authStore.refreshAccessToken()
        if (refreshed) {
          processQueue(null, authStore.accessToken)
          // Update the authorization header for the original request
          originalRequest.headers['Authorization'] = `Bearer ${authStore.accessToken}`
          // Retry the original request
          return axios.request(originalRequest)
        } else {
          processQueue(new Error('Token refresh failed'), null)
          // Refresh failed, clear auth and redirect
          authStore.clearAuth()
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
          return Promise.reject(error)
        }
      } catch (refreshError) {
        processQueue(refreshError, null)
        // Refresh failed, clear auth and redirect
        authStore.clearAuth()
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
  )
}

export { axios }
export default axios
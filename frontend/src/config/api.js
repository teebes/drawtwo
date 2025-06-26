import axios from 'axios'

// API Configuration
const API_BASE_URL = 'http://localhost:8000/api'

// Configure axios defaults
axios.defaults.baseURL = API_BASE_URL
// Note: withCredentials is set per-request basis to avoid CSRF issues with auth endpoints

// Setup axios interceptor for automatic token refresh
// Note: This will be initialized after the auth store is available
let authStore = null
let isRefreshing = false // Circuit breaker to prevent multiple simultaneous refresh attempts

export const initializeAuthInterceptor = (store) => {
  authStore = store

  axios.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config

      // Don't try to refresh for these conditions:
      // 1. Not a 401 error
      // 2. No refresh token available
      // 3. Already tried refreshing this request
      // 4. Request is to the refresh endpoint itself (prevent infinite loop!)
      // 5. Already in the middle of refreshing
      if (
        error.response?.status !== 401 ||
        !authStore?.refreshToken ||
        originalRequest._retry ||
        originalRequest.url?.includes('/auth/token/refresh/') ||
        isRefreshing
      ) {
        // If it's a 401 and we can't/won't refresh, clear auth and redirect
        if (error.response?.status === 401 && authStore) {
          authStore.clearAuth()
          // Redirect to login (avoid redirecting if already on login page)
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
        }
        return Promise.reject(error)
      }

      // Mark this request as already attempted
      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshed = await authStore.refreshAccessToken()
        if (refreshed) {
          // Update the authorization header for the original request
          originalRequest.headers['Authorization'] = `Bearer ${authStore.accessToken}`
          // Retry the original request
          return axios.request(originalRequest)
        } else {
          // Refresh failed, clear auth and redirect
          authStore.clearAuth()
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
      }
      return Promise.reject(error)
        }
      } catch (refreshError) {
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
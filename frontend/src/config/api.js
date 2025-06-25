import axios from 'axios'

// API Configuration
const API_BASE_URL = 'http://localhost:8000/api'

// Configure axios defaults
axios.defaults.baseURL = API_BASE_URL
// Note: withCredentials is set per-request basis to avoid CSRF issues with auth endpoints

// Setup axios interceptor for automatic token refresh
// Note: This will be initialized after the auth store is available
let authStore = null

export const initializeAuthInterceptor = (store) => {
  authStore = store

  axios.interceptors.response.use(
    (response) => response,
    async (error) => {
      if (error.response?.status === 401 && authStore?.refreshToken) {
        const refreshed = await authStore.refreshAccessToken()
        if (refreshed) {
          // Retry the original request
          const originalRequest = error.config
          originalRequest.headers['Authorization'] = `Bearer ${authStore.accessToken}`
          return axios.request(originalRequest)
        }
      }
      return Promise.reject(error)
    }
  )
}

export { axios }
export default axios
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth.js'
import { initializeAuthInterceptor } from './config/api.js'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Initialize authentication state
const authStore = useAuthStore()
authStore.initAuth()

// Initialize the auth interceptor now that the store is available
initializeAuthInterceptor(authStore)

app.mount('#app')
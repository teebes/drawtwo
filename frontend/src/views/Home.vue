<template>
  <div class="home">
    <header class="header">
      <div class="header-content">
        <h1>DrawTwo</h1>
        <nav class="nav">
          <router-link to="/login" class="btn btn-primary">Login / Sign Up</router-link>
        </nav>
      </div>
    </header>

    <main class="main-content">
      <section class="hero">
        <h2>Welcome to DrawTwo</h2>
        <p>A collaborative drawing application where creativity meets technology</p>

        <div class="features">
          <div class="feature">
            <h3>🎨 Collaborative Drawing</h3>
            <p>Draw together in real-time with friends and colleagues</p>
          </div>
          <div class="feature">
            <h3>🔐 Secure Authentication</h3>
            <p>Sign in with Google or get a magic link via email</p>
          </div>
          <div class="feature">
            <h3>☁️ Cloud Sync</h3>
            <p>Your drawings are saved and synced across all devices</p>
          </div>
        </div>

        <div class="cta">
          <router-link to="/login" class="btn btn-large btn-primary">
            Get Started
          </router-link>
        </div>
      </section>

      <section class="backend-status">
        <h3>System Status</h3>
        <div class="status-indicator" :class="{ online: backendOnline, offline: !backendOnline }">
          Backend: {{ backendOnline ? 'Online' : 'Offline' }}
        </div>
        <button @click="testBackend" :disabled="loading" class="btn btn-secondary">
          {{ loading ? 'Testing...' : 'Test Connection' }}
        </button>
        <div v-if="backendResponse" class="response">
          {{ backendResponse }}
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  name: 'Home',
  setup() {
    const backendOnline = ref(false)
    const loading = ref(false)
    const backendResponse = ref('')

    const checkBackend = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/health/')
        if (response.ok) {
          backendOnline.value = true
          return await response.json()
        }
      } catch (error) {
        console.error('Backend check failed:', error)
      }
      backendOnline.value = false
      return null
    }

    const testBackend = async () => {
      loading.value = true
      backendResponse.value = ''

      try {
        const data = await checkBackend()
        if (data) {
          backendResponse.value = `✅ Success: ${JSON.stringify(data)}`
        } else {
          backendResponse.value = '❌ Failed to connect to backend'
        }
      } catch (error) {
        backendResponse.value = `❌ Error: ${error.message}`
      }

      loading.value = false
    }

    onMounted(() => {
      checkBackend()
    })

    return {
      backendOnline,
      loading,
      backendResponse,
      testBackend
    }
  }
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.header {
  padding: 1rem 0;
  background: rgba(0, 0, 0, 0.1);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h1 {
  margin: 0;
  font-size: 2rem;
  font-weight: bold;
}

.nav {
  display: flex;
  gap: 1rem;
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 4rem 2rem;
}

.hero {
  text-align: center;
  margin-bottom: 4rem;
}

.hero h2 {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.hero p {
  font-size: 1.25rem;
  margin-bottom: 3rem;
  opacity: 0.9;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin-bottom: 3rem;
}

.feature {
  background: rgba(255, 255, 255, 0.1);
  padding: 2rem;
  border-radius: 12px;
  backdrop-filter: blur(10px);
}

.feature h3 {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
}

.feature p {
  margin: 0;
  opacity: 0.9;
}

.cta {
  margin-top: 3rem;
}

.backend-status {
  background: rgba(255, 255, 255, 0.1);
  padding: 2rem;
  border-radius: 12px;
  text-align: center;
  backdrop-filter: blur(10px);
}

.backend-status h3 {
  margin: 0 0 1rem 0;
}

.status-indicator {
  display: inline-block;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-weight: bold;
  margin-bottom: 1rem;
}

.status-indicator.online {
  background: rgba(72, 187, 120, 0.3);
  color: #68d391;
}

.status-indicator.offline {
  background: rgba(245, 101, 101, 0.3);
  color: #fc8181;
}

.btn {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.2s;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary {
  background: #4299e1;
  color: white;
}

.btn-primary:hover {
  background: #3182ce;
  transform: translateY(-1px);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.3);
}

.btn-large {
  padding: 1rem 2rem;
  font-size: 1.125rem;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.response {
  margin-top: 1rem;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  font-family: monospace;
  font-size: 0.875rem;
  word-break: break-all;
}
</style>
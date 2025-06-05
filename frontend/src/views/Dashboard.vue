<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <div class="header-content">
        <h1>DrawTwo Dashboard</h1>
        <div class="user-info">
          <span v-if="authStore.user">
            Welcome, {{ authStore.user.display_name }}!
          </span>
          <button @click="handleLogout" class="btn btn-secondary">
            Logout
          </button>
        </div>
      </div>
    </header>

    <main class="dashboard-content">
      <div class="dashboard-grid">
        <!-- User Profile Card -->
        <div class="card">
          <h2>👤 Your Profile</h2>
          <div v-if="authStore.user" class="profile-info">
            <div class="info-item">
              <strong>Email:</strong> {{ authStore.user.email }}
            </div>
            <div class="info-item" v-if="authStore.user.username">
              <strong>Username:</strong> {{ authStore.user.username }}
            </div>
            <div class="info-item">
              <strong>Verified:</strong>
              <span :class="{ verified: authStore.user.is_email_verified, unverified: !authStore.user.is_email_verified }">
                {{ authStore.user.is_email_verified ? '✅ Verified' : '❌ Not Verified' }}
              </span>
            </div>
            <div class="info-item">
              <strong>Member since:</strong> {{ formatDate(authStore.user.created_at) }}
            </div>
          </div>
        </div>

        <!-- API Test Card -->
        <div class="card">
          <h2>🔒 Authentication Test</h2>
          <p>Test the protected API endpoint to verify authentication is working correctly.</p>

          <button
            @click="testProtectedAPI"
            :disabled="testing"
            class="btn btn-primary"
          >
            {{ testing ? 'Testing...' : 'Test Protected Endpoint' }}
          </button>

          <div v-if="apiTestResult" class="api-result" :class="{ success: apiTestSuccess, error: !apiTestSuccess }">
            <h4>{{ apiTestSuccess ? '✅ Success' : '❌ Error' }}</h4>
            <pre>{{ JSON.stringify(apiTestResult, null, 2) }}</pre>
          </div>
        </div>

        <!-- Future Features -->
        <div class="card">
          <h2>🚧 Coming Soon</h2>
          <div class="feature-list">
            <div class="feature-item">
              <h3>🎨 Drawing Canvas</h3>
              <p>Create and collaborate on drawings in real-time</p>
            </div>
            <div class="feature-item">
              <h3>📚 Card Library</h3>
              <p>Browse and manage your card collection</p>
            </div>
            <div class="feature-item">
              <h3>🎮 Game Rooms</h3>
              <p>Join multiplayer drawing and guessing games</p>
            </div>
            <div class="feature-item">
              <h3>💬 Chat System</h3>
              <p>Communicate with other players via WebSocket</p>
            </div>
          </div>
        </div>

        <!-- System Status -->
        <div class="card">
          <h2>📊 System Status</h2>
          <div class="status-grid">
            <div class="status-item">
              <strong>Authentication:</strong>
              <span class="status-badge success">✅ Active</span>
            </div>
            <div class="status-item">
              <strong>JWT Token:</strong>
              <span class="status-badge success">✅ Valid</span>
            </div>
            <div class="status-item">
              <strong>WebSocket:</strong>
              <span class="status-badge pending">🔶 Not Implemented</span>
            </div>
            <div class="status-item">
              <strong>Database:</strong>
              <span class="status-badge success">✅ Connected</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

export default {
  name: 'Dashboard',
  setup() {
    const router = useRouter()
    const authStore = useAuthStore()

    const testing = ref(false)
    const apiTestResult = ref(null)
    const apiTestSuccess = ref(false)

    const formatDate = (dateString) => {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    }

    const testProtectedAPI = async () => {
      testing.value = true
      apiTestResult.value = null

      try {
        const result = await authStore.testProtectedEndpoint()
        apiTestResult.value = result.data || result.error
        apiTestSuccess.value = result.success
      } catch (error) {
        apiTestResult.value = error
        apiTestSuccess.value = false
      } finally {
        testing.value = false
      }
    }

    const handleLogout = async () => {
      await authStore.logout()
      router.push('/')
    }

    onMounted(async () => {
      // Refresh user data when component mounts
      if (authStore.isAuthenticated) {
        await authStore.getCurrentUser()
      }
    })

    return {
      authStore,
      testing,
      apiTestResult,
      apiTestSuccess,
      formatDate,
      testProtectedAPI,
      handleLogout
    }
  }
}
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: #f7fafc;
}

.dashboard-header {
  background: white;
  border-bottom: 1px solid #e2e8f0;
  padding: 1rem 0;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h1 {
  margin: 0;
  color: #2d3748;
  font-size: 1.75rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: #4a5568;
}

.dashboard-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 2rem;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
}

.card h2 {
  margin: 0 0 1.5rem 0;
  color: #2d3748;
  font-size: 1.25rem;
}

.profile-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f7fafc;
}

.info-item:last-child {
  border-bottom: none;
}

.verified {
  color: #22543d;
}

.unverified {
  color: #742a2a;
}

.api-result {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid;
}

.api-result.success {
  background: #f0fff4;
  border-color: #9ae6b4;
  color: #22543d;
}

.api-result.error {
  background: #fed7d7;
  border-color: #feb2b2;
  color: #742a2a;
}

.api-result h4 {
  margin: 0 0 0.5rem 0;
}

.api-result pre {
  margin: 0;
  font-size: 0.875rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.feature-item {
  padding: 1rem;
  background: #f7fafc;
  border-radius: 6px;
  border-left: 4px solid #4299e1;
}

.feature-item h3 {
  margin: 0 0 0.5rem 0;
  color: #2d3748;
  font-size: 1rem;
}

.feature-item p {
  margin: 0;
  color: #718096;
  font-size: 0.875rem;
}

.status-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #f7fafc;
  border-radius: 6px;
}

.status-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-badge.success {
  background: #c6f6d5;
  color: #22543d;
}

.status-badge.pending {
  background: #faf089;
  color: #744210;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
}

.btn-primary {
  background: #4299e1;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #3182ce;
}

.btn-secondary {
  background: #718096;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #4a5568;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
<template>
  <div id="app">
    <header class="header">
      <h1>DrawTwo</h1>
      <div class="status" :class="{ online: backendOnline, offline: !backendOnline }">
        Backend: {{ backendOnline ? 'Online' : 'Offline' }}
      </div>
    </header>

    <main class="main-content">
      <div class="welcome">
        <h2>Welcome to DrawTwo</h2>
        <p>A collaborative drawing application</p>

        <div class="backend-test">
          <button @click="testBackend" :disabled="loading">
            {{ loading ? 'Testing...' : 'Test Backend Connection' }}
          </button>
          <div v-if="backendResponse" class="response">
            {{ backendResponse }}
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  name: 'App',
  setup() {
    const backendOnline = ref(false)
    const loading = ref(false)
    const backendResponse = ref('')

    const checkBackend = async () => {
      try {
        const response = await fetch('/api/health/')
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
          backendResponse.value = `Success: ${JSON.stringify(data)}`
        } else {
          backendResponse.value = 'Failed to connect to backend'
        }
      } catch (error) {
        backendResponse.value = `Error: ${error.message}`
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
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.header h1 {
  margin: 0;
  color: #333;
}

.status {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: bold;
}

.status.online {
  background: #d4edda;
  color: #155724;
}

.status.offline {
  background: #f8d7da;
  color: #721c24;
}

.main-content {
  padding: 2rem;
}

.welcome {
  text-align: center;
  max-width: 600px;
  margin: 0 auto;
}

.welcome h2 {
  color: #333;
  margin-bottom: 0.5rem;
}

.welcome p {
  color: #666;
  margin-bottom: 2rem;
}

.backend-test {
  margin-top: 2rem;
}

.backend-test button {
  background: #007bff;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.backend-test button:hover:not(:disabled) {
  background: #0056b3;
}

.backend-test button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.response {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
<template>
  <div class="email-confirm">
    <div class="confirm-container">
      <div class="confirm-card">
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <h2>Confirming your email...</h2>
          <p>Please wait while we verify your email address.</p>
        </div>

        <div v-else-if="success" class="success-state">
          <div class="success-icon">✅</div>
          <h2>Email Confirmed!</h2>
          <p>Your email has been successfully verified and you are now logged in.</p>
          <div class="user-info" v-if="authStore.user">
            <p>Welcome, <strong>{{ authStore.user.display_name }}</strong>!</p>
          </div>
          <div class="actions">
            <router-link to="/dashboard" class="btn btn-primary">
              Go to Dashboard
            </router-link>
          </div>
        </div>

        <div v-else class="error-state">
          <div class="error-icon">❌</div>
          <h2>Confirmation Failed</h2>
          <p>{{ errorMessage }}</p>
          <div class="actions">
            <router-link to="/login" class="btn btn-primary">
              Back to Login
            </router-link>
            <router-link to="/" class="btn btn-secondary">
              Go Home
            </router-link>
          </div>
        </div>

        <div class="footer">
          <p>
            Having trouble?
            <router-link to="/login" class="link">Contact support</router-link>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

export default {
  name: 'EmailConfirm',
  setup() {
    const route = useRoute()
    const router = useRouter()
    const authStore = useAuthStore()

    const loading = ref(true)
    const success = ref(false)
    const errorMessage = ref('')

    const confirmEmail = async () => {
      const key = route.params.key

      if (!key) {
        loading.value = false
        errorMessage.value = 'Invalid confirmation link. The confirmation key is missing.'
        return
      }

      try {
        const result = await authStore.confirmEmail(key)

        if (result.success) {
          success.value = true
          // Redirect to dashboard after a short delay
          setTimeout(() => {
            router.push('/dashboard')
          }, 3000)
        } else {
          errorMessage.value = result.error?.error || result.error?.message || 'Email confirmation failed. The link may be invalid or expired.'
        }
      } catch (error) {
        console.error('Email confirmation error:', error)
        errorMessage.value = 'An unexpected error occurred. Please try again later.'
      } finally {
        loading.value = false
      }
    }

    onMounted(() => {
      confirmEmail()
    })

    return {
      loading,
      success,
      errorMessage,
      authStore
    }
  }
}
</script>

<style scoped>
.email-confirm {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.confirm-container {
  width: 100%;
  max-width: 500px;
}

.confirm-card {
  background: white;
  border-radius: 12px;
  padding: 3rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  text-align: center;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top: 4px solid #4299e1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.success-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.success-icon,
.error-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

h2 {
  margin: 0;
  color: #2d3748;
  font-size: 1.75rem;
}

p {
  margin: 0;
  color: #718096;
  line-height: 1.6;
}

.user-info {
  background: #f0fff4;
  border: 1px solid #9ae6b4;
  border-radius: 6px;
  padding: 1rem;
  margin: 1rem 0;
}

.user-info p {
  margin: 0;
  color: #22543d;
}

.actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
  flex-wrap: wrap;
  justify-content: center;
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
  min-width: 120px;
}

.btn-primary {
  background: #4299e1;
  color: white;
}

.btn-primary:hover {
  background: #3182ce;
}

.btn-secondary {
  background: #718096;
  color: white;
}

.btn-secondary:hover {
  background: #4a5568;
}

.footer {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.footer p {
  font-size: 0.875rem;
  color: #a0aec0;
}

.link {
  color: #4299e1;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

@media (max-width: 640px) {
  .confirm-card {
    padding: 2rem;
  }

  .actions {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}
</style>
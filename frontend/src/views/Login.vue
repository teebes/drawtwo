<template>
  <div class="login">
    <div class="login-container">
      <div class="login-card">
        <h1>Welcome to DrawTwo</h1>
        <p class="subtitle">Sign in or create an account to get started</p>

        <!-- Error/Success Messages -->
        <div v-if="message" class="message" :class="messageType">
          {{ message }}
        </div>

        <!-- Login/Register Form -->
        <form @submit.prevent="handleSubmit" class="auth-form">
          <div class="form-group">
            <label for="email">Email Address</label>
            <input
              id="email"
              v-model="email"
              type="email"
              required
              placeholder="Enter your email"
              :disabled="authStore.loading"
            />
          </div>

          <div class="form-group" v-if="isSignUp">
            <label for="firstName">First Name (Optional)</label>
            <input
              id="firstName"
              v-model="firstName"
              type="text"
              placeholder="Enter your first name"
              :disabled="authStore.loading"
            />
          </div>

          <div class="form-group" v-if="isSignUp">
            <label for="lastName">Last Name (Optional)</label>
            <input
              id="lastName"
              v-model="lastName"
              type="text"
              placeholder="Enter your last name"
              :disabled="authStore.loading"
            />
          </div>

          <button
            type="submit"
            class="btn btn-primary btn-full"
            :disabled="authStore.loading || !email"
          >
            {{ authStore.loading ? 'Please wait...' : (isSignUp ? 'Sign Up' : 'Send Login Link') }}
          </button>
        </form>

        <div class="auth-divider">
          <span>or</span>
        </div>

        <!-- Google Login -->
        <button
          @click="handleGoogleLogin"
          class="btn btn-google btn-full"
          :disabled="authStore.loading"
        >
          <span class="google-icon">G</span>
          Continue with Google
        </button>

        <!-- Toggle between Login/Register -->
        <div class="auth-toggle">
          <button
            @click="toggleMode"
            class="link-button"
            type="button"
          >
            {{ isSignUp ? 'Already have an account? Sign in' : 'New to DrawTwo? Create an account' }}
          </button>
        </div>

        <!-- Back to Home -->
        <div class="back-link">
          <router-link to="/" class="link-button">← Back to Home</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

export default {
  name: 'Login',
  setup() {
    const router = useRouter()
    const authStore = useAuthStore()

    const email = ref('')
    const firstName = ref('')
    const lastName = ref('')
    const isSignUp = ref(false)
    const message = ref('')
    const messageType = ref('info')

    const showMessage = (text, type = 'info') => {
      message.value = text
      messageType.value = type
      setTimeout(() => {
        message.value = ''
      }, 5000)
    }

    const toggleMode = () => {
      isSignUp.value = !isSignUp.value
      message.value = ''
    }

    const handleSubmit = async () => {
      try {
        if (isSignUp.value) {
          // Registration
          const userData = {
            email: email.value,
            first_name: firstName.value,
            last_name: lastName.value
          }

          const result = await authStore.register(userData)

          if (result.success) {
            showMessage('Registration successful! Please check your email to verify your account.', 'success')
            // Switch to login mode
            isSignUp.value = false
          } else {
            const errorMsg = result.error?.email?.[0] || result.error?.message || 'Registration failed'
            showMessage(errorMsg, 'error')
          }
        } else {
          // Login
          const result = await authStore.sendLoginEmail(email.value)

          if (result.success) {
            showMessage('Login link sent! Please check your email and click the link to sign in.', 'success')
          } else {
            const errorMsg = result.error?.email?.[0] || result.error?.message || 'Failed to send login email'
            showMessage(errorMsg, 'error')
          }
        }
      } catch (error) {
        console.error('Auth error:', error)
        showMessage('Something went wrong. Please try again.', 'error')
      }
    }

    const handleGoogleLogin = () => {
      // For now, show a placeholder message
      // In a real implementation, you'd integrate with Google OAuth
      showMessage('Google login will be implemented with Google OAuth setup.', 'info')
    }

    return {
      email,
      firstName,
      lastName,
      isSignUp,
      message,
      messageType,
      authStore,
      toggleMode,
      handleSubmit,
      handleGoogleLogin,
      showMessage
    }
  }
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.login-container {
  width: 100%;
  max-width: 400px;
}

.login-card {
  background: white;
  border-radius: 12px;
  padding: 2.5rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}

.login-card h1 {
  margin: 0 0 0.5rem 0;
  font-size: 1.75rem;
  color: #2d3748;
  text-align: center;
}

.subtitle {
  margin: 0 0 2rem 0;
  color: #718096;
  text-align: center;
  font-size: 0.95rem;
}

.message {
  padding: 0.75rem;
  border-radius: 6px;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.message.success {
  background: #f0fff4;
  color: #22543d;
  border: 1px solid #9ae6b4;
}

.message.error {
  background: #fed7d7;
  color: #742a2a;
  border: 1px solid #feb2b2;
}

.message.info {
  background: #ebf8ff;
  color: #2c5282;
  border: 1px solid #90cdf4;
}

.auth-form {
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #4a5568;
  font-weight: 500;
  font-size: 0.875rem;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #4299e1;
  box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
}

.form-group input:disabled {
  background-color: #f7fafc;
  color: #a0aec0;
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

.btn-full {
  width: 100%;
}

.btn-primary {
  background: #4299e1;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #3182ce;
}

.btn-google {
  background: white;
  color: #4a5568;
  border: 1px solid #e2e8f0;
  gap: 0.5rem;
}

.btn-google:hover:not(:disabled) {
  background: #f7fafc;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.google-icon {
  width: 20px;
  height: 20px;
  background: #4285f4;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 12px;
}

.auth-divider {
  position: relative;
  margin: 1.5rem 0;
  text-align: center;
  color: #a0aec0;
  font-size: 0.875rem;
}

.auth-divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: #e2e8f0;
}

.auth-divider span {
  background: white;
  padding: 0 1rem;
}

.auth-toggle {
  text-align: center;
  margin-top: 1.5rem;
}

.back-link {
  text-align: center;
  margin-top: 1rem;
}

.link-button {
  background: none;
  border: none;
  color: #4299e1;
  cursor: pointer;
  font-size: 0.875rem;
  text-decoration: none;
  padding: 0;
}

.link-button:hover {
  text-decoration: underline;
}
</style>
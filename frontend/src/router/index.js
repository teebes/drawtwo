import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import EmailConfirm from '../views/EmailConfirm.vue'
import DesignReference from '../views/DesignReference.vue'
import Lobby from '../views/Lobby.vue'
import Template from '../views/Template.vue'
import Profile from '../views/Profile.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: { requiresAuth: false }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/lobby',
    name: 'Lobby',
    component: Lobby,
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/auth/email-confirm/:key',
    name: 'EmailConfirm',
    component: EmailConfirm,
    meta: { requiresAuth: false }
  },
  {
    path: '/design-reference',
    name: 'DesignReference',
    component: DesignReference,
    meta: { requiresAuth: false }
  },
  {
    path: '/template',
    name: 'Template',
    component: Template,
    meta: { requiresAuth: false }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guards
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login if route requires auth and user is not authenticated
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && authStore.isAuthenticated) {
    // Redirect to lobby if user is already authenticated and trying to access login
    next({ name: 'Lobby' })
  } else if (to.name === 'Home' && authStore.isAuthenticated) {
    // Redirect authenticated users from home to lobby
    next({ name: 'Lobby' })
  } else {
    next()
  }
})

export default router
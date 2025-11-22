import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useTitleStore } from '../stores/title'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import EmailConfirm from '../views/EmailConfirm.vue'
import ControlPanel from '../views/ControlPanel.vue'
import DesignReference from '../views/DesignReference.vue'
import GameCard from '../views/CardReference.vue'
import Lobby from '../views/Lobby.vue'
import Template from '../views/Template.vue'
import Profile from '../views/Profile.vue'
import Mockup from '../views/Mockup.vue'
import Title from '../views/Title.vue'
import TitleBriefCards from '../views/TitleBriefCards.vue'
import TitleCards from '../views/TitleCards.vue'
import CardEdit from '../views/CardEdit.vue'
import CardDetails from '../views/CardDetails.vue'
import DeckDetail from '../views/DeckDetail.vue'
import DeckEdit from '../views/DeckEdit.vue'
import GameCreate from '../views/GameCreate.vue'
import Board from '../views/Board.vue'
import Friends from '../views/Friends.vue'
import PrivacyPolicy from '../views/PrivacyPolicy.vue'
import TermsOfService from '../views/TermsOfService.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: { requiresAuth: false }
  },
  {
    path: '/privacy',
    name: 'PrivacyPolicy',
    component: PrivacyPolicy,
    meta: { requiresAuth: false }
  },
  {
    path: '/terms',
    name: 'TermsOfService',
    component: TermsOfService,
    meta: { requiresAuth: false }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/play',
    name: 'Play',
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
    path: '/friends',
    name: 'Friends',
    component: Friends,
    meta: { requiresAuth: true }
  },
  {
    path: '/:slug/leaderboard',
    name: 'Leaderboard',
    component: () => import('../views/Leaderboard.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/mockup',
    name: 'Mockup',
    component: Mockup,
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
    path: '/game-card',
    name: 'GameCard',
    component: GameCard,
    meta: { requiresAuth: false }
  },
  {
    path: '/template',
    name: 'Template',
    component: Template,
    meta: { requiresAuth: false }
  },
  {
    path: '/control',
    name: 'ControlPanel',
    component: ControlPanel,
    meta: { requiresAuth: true, requiresStaff: true }
  },
  {
    path: '/:slug/decks/new',
    name: 'DeckCreate',
    component: DeckEdit,
    meta: { requiresAuth: true }
  },
  {
    path: '/:slug/decks/:id',
    name: 'DeckDetail',
    component: DeckDetail,
    meta: { requiresAuth: true }
  },
  {
    path: '/:slug/decks/:id/edit',
    name: 'DeckEdit',
    component: DeckEdit,
    meta: { requiresAuth: true }
  },
  {
    path: '/:slug/games/new',
    name: 'GameCreate',
    component: GameCreate,
    meta: { requiresAuth: true }
  },
  {
    path: '/:slug/cards/new',
    name: 'CardCreate',
    component: CardEdit,
    meta: { requiresAuth: true }
  },
  {
    path: '/:slug/cards/:cardSlug',
    name: 'CardEdit',
    component: CardEdit,
    meta: { requiresAuth: true }
  },
  {
    path: '/:slug/cards/:cardSlug/details',
    name: 'CardDetails',
    component: CardDetails,
    meta: { requiresAuth: true }
  },
  {
    path: '/:slug/cards',
    name: 'TitleCards',
    component: TitleCards,
    meta: { requiresAuth: false }
  },
  {
    path: '/:slug/cards/brief',
    name: 'TitleBriefCards',
    component: TitleBriefCards,
    meta: { requiresAuth: false }
  },
  {
    path: '/:slug/games/:game_id',
    name: 'Board',
    component: Board,
    meta: { requiresAuth: false, hideHeader: true }
  },
  {
    path: '/:slug',
    name: 'Title',
    component: Title,
    meta: { requiresAuth: false }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// List of routes that are title-related and use /:slug pattern
const titleRoutes = [
  'Title', 'TitleCards', 'TitleBriefCards', 'CardCreate', 'CardEdit', 'CardDetails', 'DeckDetail',
  'DeckEdit', 'DeckCreate', 'GameCreate', 'Board', 'Leaderboard'
]

// Helper function to check if a route is a title route
const isTitleRoute = (routeName) => titleRoutes.includes(routeName)

// Navigation guards
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const titleStore = useTitleStore()

  // Handle authentication first
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login if route requires auth and user is not authenticated
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  } else if (to.meta.requiresStaff && (!authStore.isAuthenticated || !authStore.user?.is_staff)) {
    // Redirect to play if route requires staff and user is not staff
    next({ name: 'Play' })
    return
  } else if (to.name === 'Login' && authStore.isAuthenticated) {
    // Redirect to play if user is already authenticated and trying to access login
    next({ name: 'Play' })
    return
  }

  // Handle title loading for title routes
  if (isTitleRoute(to.name) && to.params.slug) {
    try {
      await titleStore.loadTitle(to.params.slug)
    } catch (error) {
      console.error('Failed to load title:', error)
      // Continue navigation even if title loading fails
      // The individual components can handle the error state
    }
  } else if (!isTitleRoute(to.name)) {
    // Clear title when navigating away from title routes
    titleStore.clearCurrentTitle()
  }

  next()
})

export default router
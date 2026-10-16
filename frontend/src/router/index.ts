import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

export const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true },
  },
  { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
  { path: '/customer', name: 'customer', component: () => import('../views/CustomerHomeView.vue') },
  { path: '/driver', name: 'driver', component: () => import('../views/DriverHomeView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export function createAppRouter(history = createWebHistory()) {
  const router = createRouter({ history, routes })

  router.beforeEach(async (to) => {
    const auth = useAuthStore()
    if (!to.meta.public && !auth.isAuthenticated) return { name: 'login' }
    if (to.name === 'login' && auth.isAuthenticated) return { name: 'home' }

    if (auth.isAuthenticated && !auth.user) {
      try {
        await auth.fetchMe()
      } catch {
        auth.logout()
        return { name: 'login' }
      }
    }
    // Role pages are only for users who enabled that role.
    if (to.name === 'driver' && !auth.user?.is_driver) return { name: 'home' }
    if (to.name === 'customer' && !auth.user?.is_customer) return { name: 'home' }
  })

  return router
}

import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { registerSW } from 'virtual:pwa-register'
import { setSessionExpiredHandler } from './api/client'
import App from './App.vue'
import { createAppRouter } from './router'
import { useAuthStore } from './stores/auth'
import './style.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

const router = createAppRouter()
app.use(router)

setSessionExpiredHandler(() => {
  useAuthStore().logout()
  router.push({ name: 'login' })
})

registerSW({ immediate: true })
app.mount('#app')

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { get, loadTokens, patch, post, saveTokens, type Tokens } from '../api/client'

export interface User {
  id: number
  phone: string
  name: string
  is_customer: boolean
  is_driver: boolean
  account_status: string
}

export type Role = 'customer' | 'driver'

export const useAuthStore = defineStore('auth', () => {
  const tokens = ref<Tokens | null>(loadTokens())
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!tokens.value)

  async function requestOtp(phone: string) {
    await post('/auth/otp/request/', { phone })
  }

  async function verifyOtp(phone: string, code: string) {
    const data = await post<Tokens & { user: User }>('/auth/otp/verify/', { phone, code })
    tokens.value = { access: data.access, refresh: data.refresh }
    saveTokens(tokens.value)
    user.value = data.user
  }

  async function fetchMe() {
    user.value = await get<User>('/me/')
  }

  async function updateRoles(roles: { is_customer?: boolean; is_driver?: boolean; name?: string }) {
    user.value = await patch<User>('/me/', roles)
  }

  function logout() {
    tokens.value = null
    user.value = null
    saveTokens(null)
  }

  return { tokens, user, isAuthenticated, requestOtp, verifyOtp, fetchMe, updateRoles, logout }
})

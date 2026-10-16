import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../api/client'
import { useAuthStore } from './auth'

vi.mock('../api/client', async (orig) => {
  const actual = await orig<typeof import('../api/client')>()
  return { ...actual, post: vi.fn(), get: vi.fn(), patch: vi.fn() }
})

const user = {
  id: 1,
  phone: '+201000000001',
  name: '',
  is_customer: true,
  is_driver: false,
  account_status: 'ACTIVE',
}

describe('auth store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('starts unauthenticated without stored tokens', () => {
    expect(useAuthStore().isAuthenticated).toBe(false)
  })

  it('stores tokens and user after verifying the OTP', async () => {
    vi.mocked(client.post).mockResolvedValue({ access: 'a', refresh: 'r', user })
    const auth = useAuthStore()
    await auth.verifyOtp(user.phone, '123456')
    expect(auth.isAuthenticated).toBe(true)
    expect(auth.user?.phone).toBe(user.phone)
    expect(client.loadTokens()).toEqual({ access: 'a', refresh: 'r' })
  })

  it('restores the session from storage', () => {
    client.saveTokens({ access: 'a', refresh: 'r' })
    setActivePinia(createPinia())
    expect(useAuthStore().isAuthenticated).toBe(true)
  })

  it('clears everything on logout', async () => {
    vi.mocked(client.post).mockResolvedValue({ access: 'a', refresh: 'r', user })
    const auth = useAuthStore()
    await auth.verifyOtp(user.phone, '123456')
    auth.logout()
    expect(auth.isAuthenticated).toBe(false)
    expect(auth.user).toBeNull()
    expect(client.loadTokens()).toBeNull()
  })

  it('updates roles from the API response', async () => {
    vi.mocked(client.patch).mockResolvedValue({ ...user, is_driver: true })
    const auth = useAuthStore()
    await auth.updateRoles({ is_driver: true })
    expect(auth.user?.is_driver).toBe(true)
  })
})

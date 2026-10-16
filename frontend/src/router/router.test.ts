import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory } from 'vue-router'
import { beforeEach, describe, expect, it } from 'vitest'
import { saveTokens } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { createAppRouter } from './index'

const user = { id: 1, phone: '+201', name: '', is_customer: true, is_driver: false, account_status: 'ACTIVE' }

function setup(authed: boolean, role = user) {
  localStorage.clear()
  if (authed) saveTokens({ access: 'a', refresh: 'r' })
  setActivePinia(createPinia())
  const auth = useAuthStore()
  if (authed) auth.user = role
  return createAppRouter(createMemoryHistory())
}

describe('route guards', () => {
  beforeEach(() => localStorage.clear())

  it('redirects anonymous users to login', async () => {
    const router = setup(false)
    await router.push('/customer')
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('sends authenticated users away from login', async () => {
    const router = setup(true)
    await router.push('/login')
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('blocks the driver page for non-drivers', async () => {
    const router = setup(true)
    await router.push('/driver')
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('blocks customer pages for driver-only users', async () => {
    const router = setup(true, { ...user, is_customer: false, is_driver: true })
    await router.push('/customer/requests/new')
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('matches numeric request ids only', async () => {
    const router = setup(true)
    await router.push('/customer/requests/12')
    expect(router.currentRoute.value.name).toBe('request-detail')
    await router.push('/customer/requests/abc')
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('allows the driver page for drivers', async () => {
    const router = setup(true, { ...user, is_driver: true })
    await router.push('/driver')
    expect(router.currentRoute.value.name).toBe('driver')
  })
})

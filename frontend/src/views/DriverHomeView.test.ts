import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api/driver'
import * as requests from '../api/requests'
import DriverHomeView from './DriverHomeView.vue'

vi.mock('../api/driver')
vi.mock('../api/requests')

const profile = (over: Partial<api.DriverProfile> = {}): api.DriverProfile => ({
  availability_status: 'OFFLINE',
  is_verified: false,
  current_area: null,
  location_updated_at: null,
  location_status: 'none',
  destination_area: null,
  destination_expires_at: null,
  ...over,
})

async function show(p: api.DriverProfile) {
  vi.mocked(api.fetchDriverProfile).mockResolvedValue(p)
  vi.mocked(requests.fetchAreas).mockResolvedValue([])
  const wrapper = mount(DriverHomeView, { global: { stubs: { 'router-link': true } } })
  await flushPromises()
  return wrapper
}

describe('DriverHomeView verification', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('explains pending verification and disables receiving', async () => {
    const wrapper = await show(profile())
    expect(wrapper.find('[data-testid=unverified]').exists()).toBe(true)
    const toggle = wrapper.findAll('button').find((b) => b.text() === 'ابدأ استقبال الطلبات')!
    expect(toggle.attributes('disabled')).toBeDefined()
  })

  it('lets a verified driver start receiving', async () => {
    const wrapper = await show(profile({ is_verified: true }))
    expect(wrapper.find('[data-testid=unverified]').exists()).toBe(false)
    const toggle = wrapper.findAll('button').find((b) => b.text() === 'ابدأ استقبال الطلبات')!
    expect(toggle.attributes('disabled')).toBeUndefined()
  })
})

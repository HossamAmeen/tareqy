import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api/driver'
import DriverInterestsView from './DriverInterestsView.vue'

vi.mock('../api/driver')

const request = {
  id: 1,
  pickup_area: { id: 1, name: 'المحطة' },
  destination_area: { id: 2, name: 'الأربعين' },
  notes: '',
  status: 'OPEN',
  expires_at: '',
}
const base: api.DriverInterest = { id: 1, status: 'INTERESTED', request, trip: null, customer_phone: null }

async function show(rows: api.DriverInterest[]) {
  vi.mocked(api.fetchDriverInterests).mockResolvedValue(rows)
  const wrapper = mount(DriverInterestsView, { global: { stubs: { 'router-link': true } } })
  await flushPromises()
  return wrapper
}

describe('DriverInterestsView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('hides the customer phone until contact began', async () => {
    const wrapper = await show([base])
    expect(wrapper.text()).toContain('بانتظار العميل')
    expect(wrapper.find('a').exists()).toBe(false)
  })

  it('shows the agreement and customer contact once selected', async () => {
    const trip = {
      agreed_price: '50.00',
      pickup_details: 'البوابة 2',
      scheduled_pickup_at: null,
    } as api.DriverInterest['trip']
    const wrapper = await show([{ ...base, status: 'SELECTED', trip, customer_phone: '+201000000002' }])
    expect(wrapper.text()).toContain('تم اختيارك')
    expect(wrapper.text()).toContain('50.00')
    expect(wrapper.text()).toContain('البوابة 2')
    expect(wrapper.find('a').attributes('href')).toBe('tel:+201000000002')
  })

  it('explains a rejection', async () => {
    const wrapper = await show([{ ...base, status: 'DECLINED' }])
    expect(wrapper.text()).toContain('لم يتم اختيارك')
    expect(wrapper.text()).toContain('اختار العميل سائقًا آخر')
  })
})

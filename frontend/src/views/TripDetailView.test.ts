import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Trip } from '../api/requests'
import * as reports from '../api/reports'
import * as api from '../api/trips'
import TripDetailView from './TripDetailView.vue'

vi.mock('../api/trips')
vi.mock('../api/reports')
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: '4' } }) }))

const trip = (over: Partial<Trip>): Trip => ({
  id: 4,
  trip_request: 1,
  role: 'driver',
  pickup_area: { id: 1, name: 'المحطة' },
  destination_area: { id: 2, name: 'الأربعين' },
  status: 'CONFIRMED',
  agreed_price: '50.00',
  pickup_details: '',
  scheduled_pickup_at: null,
  confirmed_at: null,
  started_at: null,
  completed_at: null,
  cancelled_at: null,
  counterpart: { id: 2, name: 'منى', phone: '+201000000009' },
  ...over,
})

async function show(t: Trip) {
  vi.mocked(api.fetchTrip).mockResolvedValue(t)
  const wrapper = mount(TripDetailView, { global: { stubs: { 'router-link': true } } })
  await flushPromises()
  return wrapper
}
const REPORT = 'الإبلاغ عن مشكلة'
const labels = (w: ReturnType<typeof mount>) =>
  w
    .findAll('button')
    .map((b) => b.text())
    .filter((t) => t !== REPORT)

describe('TripDetailView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  it('offers start and cancel to a driver on a confirmed trip', async () => {
    expect(labels(await show(trip({})))).toEqual(['بدء المشوار', 'إلغاء المشوار'])
  })

  it('does not let the customer start the trip', async () => {
    expect(labels(await show(trip({ role: 'customer' })))).toEqual(['إلغاء المشوار'])
  })

  it('offers only completion once in progress', async () => {
    const wrapper = await show(trip({ status: 'IN_PROGRESS' }))
    expect(labels(wrapper)).toEqual(['إنهاء المشوار'])
    expect(wrapper.text()).toContain('لا يمكن إلغاء مشوار بدأ')
  })

  it('has no actions on finished trips and hides contact links', async () => {
    const wrapper = await show(trip({ status: 'COMPLETED' }))
    expect(labels(wrapper)).toEqual([])
    expect(wrapper.find('a').exists()).toBe(false)
  })

  it('shows the server state returned by an action', async () => {
    vi.mocked(api.startTrip).mockResolvedValue(trip({ status: 'IN_PROGRESS' }))
    const wrapper = await show(trip({}))
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid=status]').text()).toBe('جارٍ')
  })

  it('refetches the real state when an action conflicts', async () => {
    vi.mocked(api.cancelTrip).mockRejectedValue({
      response: { data: { message: 'Cannot change a CANCELLED trip to CANCELLED.', errors: {} } },
    })
    const wrapper = await show(trip({}))
    vi.mocked(api.fetchTrip).mockResolvedValue(trip({ status: 'CANCELLED' }))
    await wrapper.findAll('button')[1].trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Cannot change')
    expect(wrapper.get('[data-testid=status]').text()).toBe('ملغي')
  })

  it('does nothing when the confirmation dialog is declined', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const wrapper = await show(trip({}))
    await wrapper.findAll('button')[1].trigger('click')
    expect(api.cancelTrip).not.toHaveBeenCalled()
  })
})

describe('TripDetailView reporting', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('files a report about the trip', async () => {
    vi.mocked(reports.reportTrip).mockResolvedValue(undefined)
    vi.mocked(api.fetchTrip).mockResolvedValue(trip({}))
    const wrapper = mount(TripDetailView, { global: { stubs: { 'router-link': true } } })
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'الإبلاغ عن مشكلة')!
      .trigger('click')
    await wrapper.find('textarea').setValue('السائق لم يحضر')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(reports.reportTrip).toHaveBeenCalledWith(4, 'السائق لم يحضر')
    expect(wrapper.text()).toContain('وصلنا بلاغك')
  })
})

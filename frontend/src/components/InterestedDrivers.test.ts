import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api/requests'
import InterestedDrivers from './InterestedDrivers.vue'

vi.mock('../api/requests')

const interest: api.Interest = {
  id: 5,
  status: 'INTERESTED',
  driver: { id: 9, name: 'أحمد', phone: '+201000000001' },
  created_at: '',
}
const trip = { id: 1, status: 'CONFIRMED' } as api.Trip

async function mountList() {
  const wrapper = mount(InterestedDrivers, { props: { requestId: 3 } })
  await flushPromises()
  return wrapper
}

describe('InterestedDrivers', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(api.fetchInterests).mockResolvedValue([interest])
  })

  it('shows call and WhatsApp links for each driver', async () => {
    const wrapper = await mountList()
    const links = wrapper.findAll('a').map((a) => a.attributes('href'))
    expect(links).toContain('tel:+201000000001')
    expect(links).toContain('https://wa.me/201000000001')
  })

  it('marks a driver as contacted and reloads', async () => {
    vi.mocked(api.markContacted).mockResolvedValue({ ...interest, status: 'CONTACTED' })
    const wrapper = await mountList()
    await wrapper.findAll('button')[0].trigger('click')
    await flushPromises()
    expect(api.markContacted).toHaveBeenCalledWith(3, 5)
    expect(api.fetchInterests).toHaveBeenCalledTimes(2)
  })

  it('confirms with the entered price and an idempotency key', async () => {
    vi.mocked(api.confirmTrip).mockResolvedValue(trip)
    const wrapper = await mountList()
    await wrapper.find('[data-testid=interest] button:last-of-type').trigger('click')
    await wrapper.find('input[type=number]').setValue('40')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(api.confirmTrip).toHaveBeenCalledWith(
      3,
      { interest: 5, agreed_price: '40', pickup_details: '' },
      expect.any(String),
    )
    expect(wrapper.emitted('confirmed')).toHaveLength(1)
  })

  it('shows the server conflict and reloads the list when confirmation fails', async () => {
    vi.mocked(api.confirmTrip).mockRejectedValue({
      response: { data: { message: 'The request is CONFIRMED and can no longer be changed.', errors: {} } },
    })
    const wrapper = await mountList()
    await wrapper.find('[data-testid=interest] button:last-of-type').trigger('click')
    await wrapper.find('input[type=number]').setValue('40')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('can no longer be changed')
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.emitted('confirmed')).toBeUndefined()
  })

  it('requires a price before confirming', async () => {
    const wrapper = await mountList()
    await wrapper.find('[data-testid=interest] button:last-of-type').trigger('click')
    expect(wrapper.find('form button[type=submit]').attributes('disabled')).toBeDefined()
  })
})

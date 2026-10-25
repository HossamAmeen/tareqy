import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api/driver'
import DriverRequestsView from './DriverRequestsView.vue'

vi.mock('../api/driver')

const row: api.MatchedRequest = {
  id: 7,
  pickup_area: { id: 1, name: 'المحطة' },
  destination_area: { id: 2, name: 'الأربعين' },
  notes: '',
  preferred_pickup_at: null,
  expires_at: '2030-01-01T00:00:00Z',
  match_type: 'estimated',
  my_interest: null,
}

const mountView = () => mount(DriverRequestsView, { global: { stubs: { 'router-link': true } } })

describe('DriverRequestsView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('lists matches and shows an interest button', async () => {
    vi.mocked(api.fetchMatchingRequests).mockResolvedValue([row])
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('المحطة ← الأربعين')
    expect(wrapper.find('button').text()).toBe('مهتم')
  })

  it('expresses interest and flips to withdraw', async () => {
    vi.mocked(api.fetchMatchingRequests)
      .mockResolvedValueOnce([row])
      .mockResolvedValue([{ ...row, my_interest: 'INTERESTED' }])
    vi.mocked(api.expressInterest).mockResolvedValue({ status: 'INTERESTED' })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(api.expressInterest).toHaveBeenCalledWith(7)
    expect(wrapper.find('button').text()).toBe('سحب الاهتمام')
  })

  it('shows the server error and reloads when the request closed', async () => {
    vi.mocked(api.fetchMatchingRequests).mockResolvedValueOnce([row]).mockResolvedValue([])
    vi.mocked(api.expressInterest).mockRejectedValue({
      response: { data: { message: 'This request is closed.', errors: {} } },
    })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('This request is closed.')
    expect(wrapper.findAll('[data-testid=matched-request]')).toHaveLength(0)
  })

  it('states that interest is not confirmation', async () => {
    vi.mocked(api.fetchMatchingRequests).mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('لا يعني تأكيد')
  })
})

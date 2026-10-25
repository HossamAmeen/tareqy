import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api/driver'
import { useDriverStore } from './driver'

vi.mock('../api/driver')

const profile: api.DriverProfile = {
  availability_status: 'OFFLINE',
  current_area: null,
  location_updated_at: null,
  location_status: 'none',
  destination_area: null,
  destination_expires_at: null,
}
const row: api.MatchedRequest = {
  id: 1,
  pickup_area: { id: 1, name: 'A' },
  destination_area: { id: 2, name: 'B' },
  notes: '',
  preferred_pickup_at: null,
  expires_at: '',
  match_type: 'estimated',
  my_interest: null,
}

describe('driver store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('replaces the profile with the server response on update', async () => {
    vi.mocked(api.updateDriverProfile).mockResolvedValue({ ...profile, availability_status: 'AVAILABLE' })
    const store = useDriverStore()
    store.profile = profile
    await store.update({ availability_status: 'AVAILABLE' })
    expect(store.profile?.availability_status).toBe('AVAILABLE')
  })

  it('stores the freshness returned after a location report', async () => {
    vi.mocked(api.sendDriverLocation).mockResolvedValue({ ...profile, location_status: 'fresh' })
    const store = useDriverStore()
    await store.reportLocation('30.000000', '32.000000')
    expect(store.profile?.location_status).toBe('fresh')
  })

  it('expresses interest then reloads the server list', async () => {
    vi.mocked(api.expressInterest).mockResolvedValue({ status: 'INTERESTED' })
    vi.mocked(api.fetchMatchingRequests).mockResolvedValue([{ ...row, my_interest: 'INTERESTED' }])
    const store = useDriverStore()
    await store.setInterest(1, true)
    expect(api.expressInterest).toHaveBeenCalledWith(1)
    expect(store.requests[0].my_interest).toBe('INTERESTED')
  })

  it('withdraws interest', async () => {
    vi.mocked(api.withdrawInterest).mockResolvedValue({ status: 'WITHDRAWN' })
    vi.mocked(api.fetchMatchingRequests).mockResolvedValue([{ ...row, my_interest: 'WITHDRAWN' }])
    const store = useDriverStore()
    await store.setInterest(1, false)
    expect(api.withdrawInterest).toHaveBeenCalledWith(1)
  })

  it('drops requests the server no longer returns', async () => {
    vi.mocked(api.fetchMatchingRequests).mockResolvedValue([])
    const store = useDriverStore()
    store.requests = [row]
    await store.loadRequests()
    expect(store.requests).toEqual([])
  })
})

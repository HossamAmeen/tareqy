import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api/requests'
import { useRequestsStore } from './requests'

vi.mock('../api/requests')

const base = {
  pickup_area: { id: 1, name: 'A' },
  destination_area: { id: 2, name: 'B' },
  pickup_location_is_precise: false,
  notes: '',
  preferred_pickup_at: null,
  expires_at: '',
  created_at: '',
}
const open = { ...base, id: 1, status: 'OPEN' as const }

describe('requests store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('adds a created request to the top of the list', async () => {
    vi.mocked(api.createRequest).mockResolvedValue(open)
    const store = useRequestsStore()
    store.items = [{ ...open, id: 0 }]
    await store.create({ pickup_area: 1, destination_area: 2 })
    expect(store.items.map((r) => r.id)).toEqual([1, 0])
  })

  it('replaces the cached copy with the server state on cancel', async () => {
    vi.mocked(api.cancelRequest).mockResolvedValue({ ...open, status: 'CANCELLED' })
    const store = useRequestsStore()
    store.items = [open]
    await store.cancel(1)
    expect(store.items).toHaveLength(1)
    expect(store.items[0].status).toBe('CANCELLED')
  })

  it('loads areas only once', async () => {
    vi.mocked(api.fetchAreas).mockResolvedValue([{ id: 1, name: 'A' }])
    const store = useRequestsStore()
    await store.loadAreas()
    await store.loadAreas()
    expect(api.fetchAreas).toHaveBeenCalledTimes(1)
  })

  it('refresh picks up a server-side expiry', async () => {
    vi.mocked(api.fetchRequest).mockResolvedValue({ ...open, status: 'EXPIRED' })
    const store = useRequestsStore()
    store.items = [open]
    await store.refresh(1)
    expect(store.items[0].status).toBe('EXPIRED')
  })
})

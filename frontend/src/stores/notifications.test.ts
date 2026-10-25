import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api/notifications'
import { notificationTarget } from '../labels'
import { useNotificationsStore } from './notifications'

vi.mock('../api/notifications')

const note = (id: number, read_at: string | null = null): api.AppNotification => ({
  id,
  type: 'TRIP_CONFIRMED',
  title: 't',
  body: 'b',
  related_object_id: 1,
  read_at,
  created_at: '',
})

describe('notifications store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('takes list and unread count from the server', async () => {
    vi.mocked(api.fetchNotifications).mockResolvedValue({ unread_count: 2, results: [note(1), note(2)] })
    const store = useNotificationsStore()
    await store.load()
    expect(store.unread).toBe(2)
    expect(store.items).toHaveLength(2)
  })

  it('marks read once and never goes below zero', async () => {
    vi.mocked(api.markNotificationRead).mockResolvedValue(note(1, 'now'))
    const store = useNotificationsStore()
    store.items = [note(1)]
    store.unread = 1
    await store.markRead(1)
    await store.markRead(1)
    expect(store.unread).toBe(0)
    expect(store.items[0].read_at).toBe('now')
  })
})

describe('notificationTarget', () => {
  it('routes by type', () => {
    expect(notificationTarget('TRIP_STARTED', 5)).toEqual({ name: 'trip', params: { id: 5 } })
    expect(notificationTarget('DRIVER_INTERESTED', 3)).toEqual({ name: 'request-detail', params: { id: 3 } })
    expect(notificationTarget('NEW_MATCHING_REQUEST', 3)).toEqual({ name: 'driver-requests' })
    expect(notificationTarget('SOMETHING_NEW', 3)).toBeNull()
    expect(notificationTarget('TRIP_STARTED', null)).toBeNull()
  })
})

import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '../api/notifications'

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref<api.AppNotification[]>([])
  const unread = ref(0)

  // The server list is the source of truth; push is only a nudge to look at it.
  async function load() {
    const data = await api.fetchNotifications()
    items.value = data.results
    unread.value = data.unread_count
  }

  async function markRead(id: number) {
    const updated = await api.markNotificationRead(id)
    const index = items.value.findIndex((n) => n.id === id)
    if (index >= 0) {
      if (!items.value[index].read_at) unread.value = Math.max(0, unread.value - 1)
      items.value[index] = updated
    }
  }

  return { items, unread, load, markRead }
})

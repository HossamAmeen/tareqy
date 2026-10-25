import { del, get, post } from './client'

export interface AppNotification {
  id: number
  type: string
  title: string
  body: string
  related_object_id: number | null
  read_at: string | null
  created_at: string
}

export interface NotificationList {
  unread_count: number
  results: AppNotification[]
}

export interface PushConfig {
  enabled: boolean
  public_key: string
}

export const fetchNotifications = () => get<NotificationList>('/notifications/')
export const markNotificationRead = (id: number) => post<AppNotification>(`/notifications/${id}/read/`)
export const fetchPushConfig = () => get<PushConfig>('/push/public-key/')
export const savePushSubscription = (sub: { endpoint: string; p256dh: string; auth: string }) =>
  post('/push/subscription/', sub)
export const removePushSubscription = (endpoint: string) => del('/push/subscription/', { endpoint })

import { ref } from 'vue'
import * as api from '../api/notifications'

export type PushState = 'unsupported' | 'unavailable' | 'denied' | 'off' | 'on'

function urlBase64ToBytes(value: string) {
  const padded = (value + '='.repeat((4 - (value.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/')
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0))
}

const toBase64 = (buffer: ArrayBuffer | null) =>
  buffer ? btoa(String.fromCharCode(...new Uint8Array(buffer))) : ''

/** Web Push opt-in. The in-app notification list keeps working whatever this resolves to. */
export function usePush() {
  const state = ref<PushState>('off')
  const error = ref('')

  const supported = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window

  async function refresh() {
    if (!supported()) return (state.value = 'unsupported')
    if (Notification.permission === 'denied') return (state.value = 'denied')
    try {
      const reg = await navigator.serviceWorker.ready
      state.value = (await reg.pushManager.getSubscription()) ? 'on' : 'off'
    } catch {
      state.value = 'off'
    }
  }

  async function enable() {
    error.value = ''
    if (!supported()) return (state.value = 'unsupported')
    try {
      const config = await api.fetchPushConfig()
      if (!config.enabled) return (state.value = 'unavailable')
      if ((await Notification.requestPermission()) !== 'granted') return (state.value = 'denied')
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToBytes(config.public_key),
      })
      await api.savePushSubscription({
        endpoint: sub.endpoint,
        p256dh: toBase64(sub.getKey('p256dh')),
        auth: toBase64(sub.getKey('auth')),
      })
      state.value = 'on'
    } catch {
      error.value = 'تعذر تفعيل التنبيهات، ستظل الإشعارات متاحة داخل التطبيق'
    }
  }

  async function disable() {
    try {
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.getSubscription()
      if (sub) {
        await api.removePushSubscription(sub.endpoint)
        await sub.unsubscribe()
      }
      state.value = 'off'
    } catch {
      error.value = 'تعذر إيقاف التنبيهات'
    }
  }

  return { state, error, refresh, enable, disable }
}

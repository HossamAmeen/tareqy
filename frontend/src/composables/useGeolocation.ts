import { onBeforeUnmount, ref } from 'vue'

export type GeoPermission = 'unknown' | 'granted' | 'denied' | 'unsupported'

/**
 * Foreground-only location reporting: reads the position now and every `intervalMs` while the tab is
 * visible, and hands it to `send`. Nothing runs in the background and everything stops on unmount.
 */
export function useGeolocation(
  send: (latitude: string, longitude: string) => Promise<unknown>,
  intervalMs = 30000,
) {
  const permission = ref<GeoPermission>('geolocation' in navigator ? 'unknown' : 'unsupported')
  const tracking = ref(false)
  const error = ref('')
  let timer: ReturnType<typeof setInterval> | undefined

  function report() {
    if (document.visibilityState !== 'visible' || !navigator.onLine) return
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        permission.value = 'granted'
        try {
          await send(pos.coords.latitude.toFixed(6), pos.coords.longitude.toFixed(6))
          error.value = ''
        } catch {
          error.value = 'تعذر إرسال الموقع'
        }
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          permission.value = 'denied'
          stop()
        } else {
          error.value = 'تعذر تحديد الموقع'
        }
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 },
    )
  }

  function start() {
    if (permission.value === 'unsupported' || tracking.value) return
    tracking.value = true
    report()
    timer = setInterval(report, intervalMs)
    document.addEventListener('visibilitychange', report)
  }

  function stop() {
    tracking.value = false
    clearInterval(timer)
    document.removeEventListener('visibilitychange', report)
  }

  onBeforeUnmount(stop)

  return { permission, tracking, error, start, stop, refreshNow: report }
}

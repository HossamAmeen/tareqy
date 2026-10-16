import { onBeforeUnmount, onMounted } from 'vue'

/** Run `fn` now and every `intervalMs` while the tab is visible; also when the app regains focus/connectivity. */
export function usePolling(fn: () => void | Promise<void>, intervalMs = 15000) {
  let timer: ReturnType<typeof setInterval> | undefined

  const tick = () => {
    if (document.visibilityState === 'visible' && navigator.onLine) void fn()
  }

  onMounted(() => {
    tick()
    timer = setInterval(tick, intervalMs)
    document.addEventListener('visibilitychange', tick)
    window.addEventListener('online', tick)
  })
  onBeforeUnmount(() => {
    clearInterval(timer)
    document.removeEventListener('visibilitychange', tick)
    window.removeEventListener('online', tick)
  })
}

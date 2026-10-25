import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api/notifications'
import { usePush } from './usePush'

vi.mock('../api/notifications')

const subscription = {
  endpoint: 'https://push.example/x',
  getKey: () => new Uint8Array([1, 2, 3]).buffer,
  unsubscribe: vi.fn(),
}
const pushManager = { getSubscription: vi.fn(), subscribe: vi.fn() }

function setSupport(on: boolean) {
  if (on) {
    Object.defineProperty(navigator, 'serviceWorker', {
      value: { ready: Promise.resolve({ pushManager }) },
      configurable: true,
    })
    vi.stubGlobal('PushManager', class {})
    vi.stubGlobal('Notification', {
      permission: 'default',
      requestPermission: vi.fn().mockResolvedValue('granted'),
    })
  } else {
    Reflect.deleteProperty(navigator, 'serviceWorker')
    vi.stubGlobal('PushManager', undefined)
    Reflect.deleteProperty(window, 'PushManager')
  }
}

describe('usePush', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.unstubAllGlobals()
    pushManager.getSubscription.mockResolvedValue(null)
    pushManager.subscribe.mockResolvedValue(subscription)
  })

  it('reports unsupported browsers without throwing', async () => {
    setSupport(false)
    const push = usePush()
    await push.refresh()
    await push.enable()
    expect(push.state.value).toBe('unsupported')
  })

  it('stays unavailable when the server has no VAPID keys', async () => {
    setSupport(true)
    vi.mocked(api.fetchPushConfig).mockResolvedValue({ enabled: false, public_key: '' })
    const push = usePush()
    await push.enable()
    expect(push.state.value).toBe('unavailable')
    expect(pushManager.subscribe).not.toHaveBeenCalled()
  })

  it('subscribes and registers the endpoint with the server', async () => {
    setSupport(true)
    vi.mocked(api.fetchPushConfig).mockResolvedValue({ enabled: true, public_key: 'AQAB' })
    vi.mocked(api.savePushSubscription).mockResolvedValue(undefined)
    const push = usePush()
    await push.enable()
    expect(push.state.value).toBe('on')
    expect(api.savePushSubscription).toHaveBeenCalledWith(
      expect.objectContaining({ endpoint: 'https://push.example/x' }),
    )
  })

  it('does not subscribe when the user denies permission', async () => {
    setSupport(true)
    vi.mocked(api.fetchPushConfig).mockResolvedValue({ enabled: true, public_key: 'AQAB' })
    vi.mocked(Notification.requestPermission).mockResolvedValue('denied')
    const push = usePush()
    await push.enable()
    expect(push.state.value).toBe('denied')
    expect(pushManager.subscribe).not.toHaveBeenCalled()
  })

  it('shows a friendly error and keeps the app usable when subscribing fails', async () => {
    setSupport(true)
    vi.mocked(api.fetchPushConfig).mockResolvedValue({ enabled: true, public_key: 'AQAB' })
    pushManager.subscribe.mockRejectedValue(new Error('blocked'))
    const push = usePush()
    await push.enable()
    expect(push.error.value).toContain('داخل التطبيق')
  })

  it('unsubscribes on the server and the browser', async () => {
    setSupport(true)
    pushManager.getSubscription.mockResolvedValue(subscription)
    vi.mocked(api.removePushSubscription).mockResolvedValue(undefined)
    const push = usePush()
    await push.disable()
    expect(api.removePushSubscription).toHaveBeenCalledWith('https://push.example/x')
    expect(subscription.unsubscribe).toHaveBeenCalled()
    expect(push.state.value).toBe('off')
  })
})

import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { useGeolocation } from './useGeolocation'

const getCurrentPosition = vi.fn()

function setup(send = vi.fn().mockResolvedValue(undefined)) {
  let api!: ReturnType<typeof useGeolocation>
  const wrapper = mount(
    defineComponent({
      setup() {
        api = useGeolocation(send, 1000)
        return () => null
      },
    }),
  )
  return { api, send, wrapper }
}

describe('useGeolocation', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    Object.defineProperty(navigator, 'geolocation', { value: { getCurrentPosition }, configurable: true })
    getCurrentPosition.mockReset()
    getCurrentPosition.mockImplementation((ok) => ok({ coords: { latitude: 30.1234567, longitude: 32.5 } }))
  })
  afterEach(() => vi.useRealTimers())

  it('reports immediately and then periodically', async () => {
    const { api, send } = setup()
    api.start()
    await vi.advanceTimersByTimeAsync(2000)
    expect(send).toHaveBeenCalledWith('30.123457', '32.500000')
    expect(send.mock.calls.length).toBeGreaterThanOrEqual(3)
  })

  it('stops on permission denial', async () => {
    getCurrentPosition.mockImplementation((_ok, fail) => fail({ code: 1, PERMISSION_DENIED: 1 }))
    const { api, send } = setup()
    api.start()
    await vi.advanceTimersByTimeAsync(3000)
    expect(api.permission.value).toBe('denied')
    expect(api.tracking.value).toBe(false)
    expect(send).not.toHaveBeenCalled()
  })

  it('does not report while the tab is hidden', async () => {
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    const { api, send } = setup()
    api.start()
    await vi.advanceTimersByTimeAsync(3000)
    expect(send).not.toHaveBeenCalled()
    vi.restoreAllMocks()
  })

  it('stops reporting after unmount', async () => {
    const { api, send, wrapper } = setup()
    api.start()
    wrapper.unmount()
    send.mockClear()
    await vi.advanceTimersByTimeAsync(5000)
    expect(send).not.toHaveBeenCalled()
  })
})

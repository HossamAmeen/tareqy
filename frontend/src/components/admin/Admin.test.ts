import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../../api/admin'
import AdminKpis from './AdminKpis.vue'
import AdminReports from './AdminReports.vue'
import AdminUsers from './AdminUsers.vue'

vi.mock('../../api/admin')

const user = (over: Partial<api.AdminUser> = {}): api.AdminUser => ({
  id: 1,
  phone: '+201000000001',
  name: 'سائق',
  account_status: 'ACTIVE',
  is_customer: false,
  is_driver: true,
  is_staff: false,
  is_test_account: false,
  is_verified: false,
  created_at: '',
  ...over,
})

describe('AdminKpis', () => {
  beforeEach(() => vi.resetAllMocks())

  it('formats rates, durations and missing values', async () => {
    vi.mocked(api.fetchKpis).mockResolvedValue({
      window_days: 30,
      requests_published: 12,
      open_now: 2,
      interest_rate: 0.5,
      confirmation_rate: null,
      expired_rate: 0.25,
      cancelled_before_confirmation_rate: 0,
      cancelled_after_confirmation_rate: null,
      avg_seconds_to_first_interest: 120,
      avg_seconds_to_confirmation: null,
      active_drivers_24h: 3,
      customers: 4,
      returning_customers: 1,
      returning_customer_rate: 0.25,
    })
    const wrapper = mount(AdminKpis)
    await flushPromises()
    const text = wrapper.get('[data-testid=kpis]').text()
    expect(text).toContain('12')
    expect(text).toContain('50%')
    expect(text).toContain('2 د')
    expect(text).toContain('—')
  })

  it('reloads when the window changes', async () => {
    vi.mocked(api.fetchKpis).mockResolvedValue({ requests_published: 0 } as api.Kpis)
    const wrapper = mount(AdminKpis)
    await flushPromises()
    await wrapper.find('select').setValue(7)
    await flushPromises()
    expect(api.fetchKpis).toHaveBeenLastCalledWith(7)
  })
})

describe('AdminUsers', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  it('verifies a driver and shows the updated row', async () => {
    vi.mocked(api.fetchUsers).mockResolvedValue([user()])
    vi.mocked(api.userAction).mockResolvedValue(user({ is_verified: true }))
    const wrapper = mount(AdminUsers)
    await flushPromises()
    expect(wrapper.text()).toContain('غير موثّق')
    const verify = wrapper.findAll('button').find((b) => b.text() === 'توثيق السائق')!
    await verify.trigger('click')
    await flushPromises()
    expect(api.userAction).toHaveBeenCalledWith(1, 'verify-driver')
    expect(wrapper.text()).toContain('موثّق')
    expect(wrapper.text()).not.toContain('غير موثّق')
  })

  it('asks before suspending and does nothing when declined', async () => {
    vi.mocked(api.fetchUsers).mockResolvedValue([user()])
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const wrapper = mount(AdminUsers)
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'إيقاف الحساب')!
      .trigger('click')
    expect(api.userAction).not.toHaveBeenCalled()
  })

  it('shows server errors', async () => {
    vi.mocked(api.fetchUsers).mockResolvedValue([user()])
    vi.mocked(api.userAction).mockRejectedValue({
      response: { data: { message: 'You cannot change your own account status.', errors: {} } },
    })
    const wrapper = mount(AdminUsers)
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'إيقاف الحساب')!
      .trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('cannot change your own')
  })
})

describe('AdminReports', () => {
  const report: api.AdminReport = {
    id: 3,
    reporter: '+201000000001',
    related_user: { id: 2, phone: '+201000000002' },
    trip: 1,
    reason: 'السائق لم يحضر',
    status: 'OPEN',
    resolution_note: '',
    created_at: '2030-01-01T00:00:00Z',
  }
  beforeEach(() => vi.resetAllMocks())

  it('resolves a report with a note', async () => {
    vi.mocked(api.fetchReports).mockResolvedValue([report])
    vi.mocked(api.reviewReport).mockResolvedValue({ ...report, status: 'RESOLVED', resolution_note: 'تم' })
    const wrapper = mount(AdminReports)
    await flushPromises()
    await wrapper.find('input').setValue('تم')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'تمت المعالجة')!
      .trigger('click')
    await flushPromises()
    expect(api.reviewReport).toHaveBeenCalledWith(3, 'RESOLVED', 'تم')
    expect(wrapper.findAll('button')).toHaveLength(0)
    expect(wrapper.text()).toContain('RESOLVED')
  })

  it('reloads when the report was already closed elsewhere', async () => {
    vi.mocked(api.fetchReports)
      .mockResolvedValueOnce([report])
      .mockResolvedValue([{ ...report, status: 'DISMISSED' }])
    vi.mocked(api.reviewReport).mockRejectedValue({
      response: { data: { message: 'This report is already closed.', errors: {} } },
    })
    const wrapper = mount(AdminReports)
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'تمت المعالجة')!
      .trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('already closed')
    expect(wrapper.findAll('button')).toHaveLength(0)
  })
})

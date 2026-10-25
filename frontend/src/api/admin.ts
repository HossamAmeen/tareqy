import { get, post } from './client'

export interface Page<T> {
  count: number
  results: T[]
}

export interface AdminUser {
  id: number
  phone: string
  name: string
  account_status: 'ACTIVE' | 'SUSPENDED'
  is_customer: boolean
  is_driver: boolean
  is_staff: boolean
  is_test_account: boolean
  is_verified: boolean | null
  created_at: string
}

export interface AdminRequest {
  id: number
  customer: string
  pickup_area: string
  destination_area: string
  status: string
  expires_at: string
  created_at: string
  interest_count: number
}

export interface AdminReport {
  id: number
  reporter: string
  related_user: { id: number; phone: string } | null
  trip: number | null
  reason: string
  status: 'OPEN' | 'REVIEWING' | 'RESOLVED' | 'DISMISSED'
  resolution_note: string
  created_at: string
}

export interface Kpis {
  window_days: number
  requests_published: number
  open_now: number
  interest_rate: number | null
  confirmation_rate: number | null
  expired_rate: number | null
  cancelled_before_confirmation_rate: number | null
  cancelled_after_confirmation_rate: number | null
  avg_seconds_to_first_interest: number | null
  avg_seconds_to_confirmation: number | null
  active_drivers_24h: number
  customers: number
  returning_customers: number
  returning_customer_rate: number | null
}

const qs = (params: Record<string, string | undefined>) => {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v) search.set(k, v)
  const text = search.toString()
  return text ? `?${text}` : ''
}

export const fetchKpis = (days: number) => get<Kpis>(`/admin/kpis/?days=${days}`)
export const fetchUsers = async (params: { search?: string; role?: string }) =>
  (await get<Page<AdminUser>>(`/admin/users/${qs(params)}`)).results
export const userAction = (
  id: number,
  action: 'suspend' | 'activate' | 'verify-driver' | 'unverify-driver',
) => post<AdminUser>(`/admin/users/${id}/${action}/`)
export const fetchAdminRequests = async (status?: string) =>
  (await get<Page<AdminRequest>>(`/admin/requests/${qs({ status })}`)).results
export const fetchReports = async (status?: string) =>
  (await get<Page<AdminReport>>(`/admin/reports/${qs({ status })}`)).results
export const reviewReport = (id: number, status: 'REVIEWING' | 'RESOLVED' | 'DISMISSED', note = '') =>
  post<AdminReport>(`/admin/reports/${id}/review/`, { status, note })

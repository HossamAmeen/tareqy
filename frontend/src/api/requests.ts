import { get, patch, post } from './client'

export interface Area {
  id: number
  name: string
}

export type RequestStatus = 'OPEN' | 'CONFIRMED' | 'CANCELLED' | 'EXPIRED'

export interface TripRequest {
  id: number
  pickup_area: Area
  destination_area: Area
  pickup_location_is_precise: boolean
  notes: string
  preferred_pickup_at: string | null
  status: RequestStatus
  expires_at: string
  created_at: string
}

export interface RequestPayload {
  pickup_area: number
  destination_area: number
  notes?: string
  preferred_pickup_at?: string | null
  pickup_latitude?: string
  pickup_longitude?: string
}

interface Page<T> {
  count: number
  results: T[]
}

export const fetchAreas = () => get<Area[]>('/areas/')
export const fetchRequests = async () => (await get<Page<TripRequest>>('/requests/')).results
export const fetchRequest = (id: number) => get<TripRequest>(`/requests/${id}/`)
export const createRequest = (payload: RequestPayload) => post<TripRequest>('/requests/', payload)
export const updateRequest = (id: number, payload: Partial<RequestPayload>) =>
  patch<TripRequest>(`/requests/${id}/`, payload)
export const cancelRequest = (id: number) => post<TripRequest>(`/requests/${id}/cancel/`)

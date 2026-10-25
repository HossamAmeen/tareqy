import { get, patch, post } from './client'

export interface Area {
  id: number
  name: string
}

export type RequestStatus = 'OPEN' | 'CONFIRMED' | 'CANCELLED' | 'EXPIRED'

export interface Person {
  id: number
  name: string
  phone: string
}

export interface Trip {
  id: number
  trip_request: number
  role: 'customer' | 'driver'
  pickup_area: Area
  destination_area: Area
  status: 'CONFIRMED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
  agreed_price: string | null
  pickup_details: string
  scheduled_pickup_at: string | null
  confirmed_at: string | null
  started_at: string | null
  completed_at: string | null
  cancelled_at: string | null
  counterpart: Person
}

export interface Interest {
  id: number
  status: 'INTERESTED' | 'CONTACTED' | 'SELECTED'
  driver: Person
  created_at: string
}

export interface ConfirmPayload {
  interest: number
  agreed_price: string
  pickup_details?: string
}

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
  trip?: Trip | null
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
export const fetchInterests = (id: number) => get<Interest[]>(`/requests/${id}/interests/`)
export const markContacted = (id: number, interestId: number) =>
  post<Interest>(`/requests/${id}/interests/${interestId}/contacted/`)
/** `key` makes a retried confirmation return the same trip instead of a conflict. */
export const confirmTrip = (id: number, payload: ConfirmPayload, key: string) =>
  post<Trip>(`/requests/${id}/confirm/`, payload, { 'Idempotency-Key': key })

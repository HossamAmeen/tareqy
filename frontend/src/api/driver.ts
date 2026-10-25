import { del, get, patch, post } from './client'
import type { Area, Trip } from './requests'

export type Availability = 'OFFLINE' | 'AVAILABLE'
export type LocationStatus = 'none' | 'fresh' | 'stale'
export type InterestStatus = 'INTERESTED' | 'CONTACTED' | 'WITHDRAWN' | 'DECLINED' | 'SELECTED'

export interface DriverProfile {
  availability_status: Availability
  current_area: Area | null
  location_updated_at: string | null
  location_status: LocationStatus
  destination_area: Area | null
  destination_expires_at: string | null
}

export interface DriverProfilePayload {
  availability_status?: Availability
  destination_area?: number | null
  destination_ttl_minutes?: number
}

export interface MatchedRequest {
  id: number
  pickup_area: Area
  destination_area: Area
  notes: string
  preferred_pickup_at: string | null
  expires_at: string
  match_type: 'estimated'
  my_interest: InterestStatus | null
}

export const fetchDriverProfile = () => get<DriverProfile>('/driver/profile/')
export const updateDriverProfile = (payload: DriverProfilePayload) =>
  patch<DriverProfile>('/driver/profile/', payload)
export const sendDriverLocation = (latitude: string, longitude: string) =>
  post<DriverProfile>('/driver/location/', { latitude, longitude })
export const fetchMatchingRequests = () => get<MatchedRequest[]>('/driver/requests/')
export const expressInterest = (id: number) => post<{ status: InterestStatus }>(`/requests/${id}/interest/`)
export const withdrawInterest = (id: number) => del<{ status: InterestStatus }>(`/requests/${id}/interest/`)

export interface DriverInterest {
  id: number
  status: InterestStatus
  request: {
    id: number
    pickup_area: Area
    destination_area: Area
    notes: string
    status: string
    expires_at: string
  }
  trip: Trip | null
  customer_phone: string | null
}

export const fetchDriverInterests = () => get<DriverInterest[]>('/driver/interests/')

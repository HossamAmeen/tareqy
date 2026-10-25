import { get, post } from './client'
import type { Trip } from './requests'

export const fetchTrip = (id: number) => get<Trip>(`/trips/${id}/`)
export const startTrip = (id: number) => post<Trip>(`/trips/${id}/start/`)
export const completeTrip = (id: number) => post<Trip>(`/trips/${id}/complete/`)
export const cancelTrip = (id: number) => post<Trip>(`/trips/${id}/cancel/`)

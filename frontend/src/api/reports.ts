import { post } from './client'

export const reportTrip = (trip: number, reason: string) => post('/reports/', { trip, reason })

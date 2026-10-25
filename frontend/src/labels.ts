import type { LocationStatus } from './api/driver'
import type { RequestStatus } from './api/requests'

export const STATUS_LABELS: Record<RequestStatus, string> = {
  OPEN: 'مفتوح',
  CONFIRMED: 'مؤكد',
  CANCELLED: 'ملغي',
  EXPIRED: 'منتهي',
}

export const isEditable = (status: RequestStatus) => status === 'OPEN'

export function formatDateTime(iso: string) {
  return new Intl.DateTimeFormat('ar-EG', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso))
}

export const LOCATION_STATUS_LABELS: Record<LocationStatus, string> = {
  none: 'غير محدد بعد',
  fresh: 'حديث',
  stale: 'قديم، افتح التطبيق لتحديثه',
}

export const INTEREST_LABELS: Record<string, string> = {
  INTERESTED: 'بانتظار العميل',
  CONTACTED: 'تم التواصل معك',
  DECLINED: 'لم يتم اختيارك',
  SELECTED: 'تم اختيارك',
}

export const phoneHref = (phone: string) => `tel:${phone}`
export const whatsappHref = (phone: string) => `https://wa.me/${phone.replace(/\D/g, '')}`

export const TRIP_STATUS_LABELS: Record<string, string> = {
  CONFIRMED: 'مؤكد',
  IN_PROGRESS: 'جارٍ',
  COMPLETED: 'مكتمل',
  CANCELLED: 'ملغي',
}

/** Where a notification leads. Customers get request pages, drivers get their own screens. */
export function notificationTarget(type: string, id: number | null) {
  if (id === null) return null
  switch (type) {
    case 'DRIVER_INTERESTED':
    case 'REQUEST_EXPIRING':
      return { name: 'request-detail', params: { id } }
    case 'TRIP_CONFIRMED':
    case 'TRIP_STARTED':
    case 'TRIP_COMPLETED':
    case 'TRIP_CANCELLED':
      return { name: 'trip', params: { id } }
    case 'NEW_MATCHING_REQUEST':
      return { name: 'driver-requests' }
    case 'CUSTOMER_CONTACTED':
    case 'INTEREST_NOT_SELECTED':
    case 'REQUEST_CHANGED':
    case 'REQUEST_CANCELLED':
    case 'REQUEST_EXPIRED':
      return { name: 'driver-interests' }
    default:
      return null
  }
}

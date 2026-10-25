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

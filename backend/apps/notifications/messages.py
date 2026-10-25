"""Push/in-app wording per notification type. Never include names, phones or exact locations."""

MESSAGES = {
    'NEW_MATCHING_REQUEST': ('طلب جديد مناسب', 'يوجد طلب جديد مناسب لوجهتك.'),
    'DRIVER_INTERESTED': ('سائق مهتم', 'أبدى سائق اهتمامه بطلبك.'),
    'CUSTOMER_CONTACTED': ('بدأ التواصل', 'بدأ العميل التواصل معك بخصوص طلب.'),
    'TRIP_CONFIRMED': ('تم تأكيد المشوار', 'تم تأكيد مشوار، افتح التطبيق للتفاصيل.'),
    'INTEREST_NOT_SELECTED': ('لم يتم اختيارك', 'اختار العميل سائقًا آخر لهذا الطلب.'),
    'REQUEST_CHANGED': ('تم تعديل الطلب', 'عُدّل طلب أبديت اهتمامك به.'),
    'REQUEST_CANCELLED': ('تم إلغاء الطلب', 'ألغى العميل طلبًا أبديت اهتمامك به.'),
    'REQUEST_EXPIRED': ('انتهى الطلب', 'انتهت صلاحية طلب أبديت اهتمامك به.'),
    'REQUEST_EXPIRING': ('طلبك سينتهي قريبًا', 'ينتهي طلبك بعد دقائق دون تأكيد.'),
    'TRIP_STARTED': ('بدأ المشوار', 'بدأ مشوارك.'),
    'TRIP_COMPLETED': ('انتهى المشوار', 'تم إكمال المشوار.'),
    'TRIP_CANCELLED': ('أُلغي المشوار', 'أُلغي مشوار مؤكد، افتح التطبيق للتفاصيل.'),
}
DEFAULT_MESSAGE = ('إشعار جديد', 'لديك إشعار جديد.')


def message_for(notification_type):
    return MESSAGES.get(notification_type, DEFAULT_MESSAGE)

from datetime import timedelta

from django.http import Http404, JsonResponse
from django.urls import include, path
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from apps.accounts.sms import LocMemSMSBackend
from apps.trips.models import TripRequest


def last_otp(request):
    """Latest verification code sent to ?phone= (the SMS outbox lives in this process)."""
    phone = request.GET.get('phone', '')
    for sent_to, message in reversed(LocMemSMSBackend.outbox):
        if sent_to == phone:
            return JsonResponse({'code': message.rsplit(' ', 1)[-1]})
    raise Http404


@csrf_exempt
def expire_request(request, pk):
    """Force a request past its expiry time, as if its TTL had elapsed."""
    updated = TripRequest.objects.filter(pk=pk).update(expires_at=timezone.now() - timedelta(seconds=1))
    if not updated:
        raise Http404
    return JsonResponse({'expired': pk})


urlpatterns = [
    path('e2e/otp/', last_otp),
    path('e2e/expire/<int:pk>/', expire_request),
    path('', include('config.urls')),
]

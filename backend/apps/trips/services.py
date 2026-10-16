from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.notifications.services import create_notification
from common.exceptions import BusinessRuleError, ConflictError

from .models import DriverInterest, StatusEvent, TripRequest

# Allowed request transitions; enforced on the server only.
REQUEST_TRANSITIONS = {
    TripRequest.Status.OPEN: {TripRequest.Status.CONFIRMED, TripRequest.Status.CANCELLED, TripRequest.Status.EXPIRED},
    TripRequest.Status.CONFIRMED: set(),
    TripRequest.Status.CANCELLED: set(),
    TripRequest.Status.EXPIRED: set(),
}

LIVE_INTEREST_STATUSES = (DriverInterest.Status.INTERESTED, DriverInterest.Status.CONTACTED)
SUBSTANTIAL_FIELDS = ('pickup_area', 'destination_area')


def record_status_event(obj, from_status, to_status, actor=None):
    """Log a status transition for a TripRequest, DriverInterest or Trip."""
    return StatusEvent.objects.create(
        object_type=type(obj).__name__,
        object_id=obj.pk,
        from_status=from_status or '',
        to_status=to_status,
        actor=actor,
    )


def _lock(trip_request):
    return TripRequest.objects.select_for_update().get(pk=trip_request.pk)


def _transition(trip_request, to_status, actor=None):
    """Move a locked request to `to_status` if the state machine allows it."""
    if to_status not in REQUEST_TRANSITIONS[trip_request.status]:
        raise ConflictError(f'Cannot change a {trip_request.status} request to {to_status}.')
    previous = trip_request.status
    trip_request.status = to_status
    trip_request.save(update_fields=['status', 'modified_at'])
    record_status_event(trip_request, previous, to_status, actor)


def _ensure_editable(trip_request):
    if trip_request.status != TripRequest.Status.OPEN:
        raise ConflictError(f'The request is {trip_request.status} and can no longer be changed.')
    if trip_request.expires_at <= timezone.now():
        raise ConflictError('The request has expired.')


def _decline_live_interests(trip_request, actor, notification_type):
    """Close interests of drivers still waiting on this request and tell them."""
    interests = list(trip_request.interests.select_for_update().filter(status__in=LIVE_INTEREST_STATUSES))
    for interest in interests:
        previous = interest.status
        interest.status = DriverInterest.Status.DECLINED
        interest.save(update_fields=['status', 'modified_at'])
        record_status_event(interest, previous, interest.status, actor)
        create_notification(
            interest.driver,
            notification_type,
            related_object_id=trip_request.pk,
            dedupe_key=f'{notification_type}:{trip_request.pk}:{interest.pk}:{trip_request.modified_at:%s%f}',
        )


def _validate_areas(pickup_area, destination_area):
    if pickup_area.pk == destination_area.pk:
        raise BusinessRuleError('Pickup and destination must be different.')
    if not (pickup_area.is_active and destination_area.is_active):
        raise BusinessRuleError('Selected area is not available.')


@transaction.atomic
def create_request(customer, *, pickup_area, destination_area, **extra):
    if not customer.is_customer:
        raise BusinessRuleError('Enable the customer role to request a trip.')
    _validate_areas(pickup_area, destination_area)
    preferred = extra.get('preferred_pickup_at')
    if preferred and preferred <= timezone.now():
        raise BusinessRuleError('Preferred pickup time must be in the future.')

    trip_request = TripRequest.objects.create(
        customer=customer,
        pickup_area=pickup_area,
        destination_area=destination_area,
        expires_at=timezone.now() + timedelta(minutes=settings.REQUEST_TTL_MINUTES),
        **extra,
    )
    record_status_event(trip_request, '', trip_request.status, customer)
    return trip_request


@transaction.atomic
def update_request(trip_request, actor, **changes):
    """Edit an OPEN request. Changing pickup or destination invalidates drivers' earlier interest."""
    trip_request = _lock(trip_request)
    _ensure_editable(trip_request)

    pickup = changes.get('pickup_area', trip_request.pickup_area)
    destination = changes.get('destination_area', trip_request.destination_area)
    _validate_areas(pickup, destination)
    preferred = changes.get('preferred_pickup_at')
    if preferred and preferred <= timezone.now():
        raise BusinessRuleError('Preferred pickup time must be in the future.')

    substantial = any(f in changes and changes[f] != getattr(trip_request, f) for f in SUBSTANTIAL_FIELDS)
    for field, value in changes.items():
        setattr(trip_request, field, value)
    if substantial:
        # A different route is a different request: stale precise coordinates no longer apply.
        if 'pickup_area' in changes and 'pickup_latitude' not in changes:
            trip_request.pickup_latitude = trip_request.pickup_longitude = None
    trip_request.save()

    if substantial:
        _decline_live_interests(trip_request, actor, 'REQUEST_CHANGED')
    return trip_request


@transaction.atomic
def cancel_request(trip_request, actor):
    trip_request = _lock(trip_request)
    if trip_request.status == TripRequest.Status.OPEN and trip_request.expires_at <= timezone.now():
        raise ConflictError('The request has expired.')
    _transition(trip_request, TripRequest.Status.CANCELLED, actor)
    _decline_live_interests(trip_request, actor, 'REQUEST_CANCELLED')
    return trip_request


def expire_due_requests(now=None):
    """Mark OPEN requests past `expires_at` as EXPIRED. Safe to run concurrently and repeatedly."""
    now = now or timezone.now()
    expired = 0
    for pk in TripRequest.objects.filter(status=TripRequest.Status.OPEN, expires_at__lte=now).values_list(
        'pk', flat=True
    ):
        with transaction.atomic():
            trip_request = TripRequest.objects.select_for_update().get(pk=pk)
            # Re-check under the lock: it may have been confirmed or cancelled meanwhile.
            if trip_request.status != TripRequest.Status.OPEN or trip_request.expires_at > now:
                continue
            _transition(trip_request, TripRequest.Status.EXPIRED)
            _decline_live_interests(trip_request, None, 'REQUEST_EXPIRED')
            expired += 1
    return expired

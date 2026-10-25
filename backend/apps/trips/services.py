from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import DriverProfile
from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from common.exceptions import BusinessRuleError, ConflictError

from .models import DriverInterest, StatusEvent, Trip, TripRequest

# Allowed request transitions; enforced on the server only.
REQUEST_TRANSITIONS = {
    TripRequest.Status.OPEN: {TripRequest.Status.CONFIRMED, TripRequest.Status.CANCELLED, TripRequest.Status.EXPIRED},
    TripRequest.Status.CONFIRMED: set(),
    TripRequest.Status.CANCELLED: set(),
    TripRequest.Status.EXPIRED: set(),
}

# Allowed trip transitions; enforced on the server only.
TRIP_TRANSITIONS = {
    Trip.Status.CONFIRMED: {Trip.Status.IN_PROGRESS, Trip.Status.CANCELLED},
    Trip.Status.IN_PROGRESS: {Trip.Status.COMPLETED},
    Trip.Status.COMPLETED: set(),
    Trip.Status.CANCELLED: set(),
}

LIVE_INTEREST_STATUSES = (DriverInterest.Status.INTERESTED, DriverInterest.Status.CONTACTED)
ACTIVE_TRIP_STATUSES = (Trip.Status.CONFIRMED, Trip.Status.IN_PROGRESS)
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
    transaction.on_commit(lambda: _notify_matching_drivers(trip_request.pk))
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


def _lock_open_request(trip_request):
    """Lock the request and make sure it can still take part in contact/confirmation."""
    trip_request = _lock(trip_request)
    if trip_request.status != TripRequest.Status.OPEN:
        raise ConflictError(f'The request is {trip_request.status} and can no longer be changed.')
    if trip_request.expires_at <= timezone.now():
        raise ConflictError('The request has expired.')
    return trip_request


@transaction.atomic
def mark_contacted(trip_request, interest_id, actor):
    """The customer started talking to an interested driver. Idempotent."""
    trip_request = _lock_open_request(trip_request)
    interest = trip_request.interests.select_for_update().filter(pk=interest_id).first()
    if interest is None:
        raise BusinessRuleError('Driver interest not found.')
    if interest.status == DriverInterest.Status.CONTACTED:
        return interest
    if interest.status != DriverInterest.Status.INTERESTED:
        raise ConflictError('This driver is no longer interested.')
    interest.status = DriverInterest.Status.CONTACTED
    interest.save(update_fields=['status', 'modified_at'])
    record_status_event(interest, DriverInterest.Status.INTERESTED, interest.status, actor)
    create_notification(
        interest.driver,
        'CUSTOMER_CONTACTED',
        related_object_id=trip_request.pk,
        dedupe_key=f'CUSTOMER_CONTACTED:{interest.pk}',
    )
    return interest


@transaction.atomic
def confirm_trip(
    trip_request, actor, *, interest_id, agreed_price, pickup_details='', scheduled_pickup_at=None, idempotency_key=''
):
    """Confirm exactly one driver for an open request. Returns (trip, created).

    Everything happens under a row lock on the request (then on the driver's profile), so two
    simultaneous confirmations serialise and the second sees a CONFIRMED request.
    """
    locked = _lock(trip_request)
    if idempotency_key and locked.status == TripRequest.Status.CONFIRMED:
        replay = (
            Trip.objects.filter(trip_request=locked, confirm_idempotency_key=idempotency_key)
            .exclude(status=Trip.Status.CANCELLED)
            .first()
        )
        if replay:
            return replay, False

    trip_request = _lock_open_request(trip_request)
    if scheduled_pickup_at and scheduled_pickup_at <= timezone.now():
        raise BusinessRuleError('Pickup time must be in the future.')

    interest = trip_request.interests.select_for_update().filter(pk=interest_id).first()
    if interest is None:
        raise BusinessRuleError('Driver interest not found.')
    if interest.status not in LIVE_INTEREST_STATUSES:
        raise ConflictError('This driver is no longer interested.')

    # Driver conflict policy: lock the driver's profile so concurrent confirmations for the same driver serialise.
    driver = interest.driver
    DriverProfile.objects.select_for_update().get_or_create(user=driver)
    if not (driver.is_driver and driver.is_active):
        raise ConflictError('This driver is not available.')
    active = Trip.objects.filter(driver=driver, status__in=ACTIVE_TRIP_STATUSES).count()
    if active >= settings.DRIVER_MAX_ACTIVE_TRIPS:
        raise ConflictError('This driver is no longer available for another trip.')

    try:
        with transaction.atomic():
            trip = Trip.objects.create(
                trip_request=trip_request,
                driver=driver,
                agreed_price=agreed_price,
                pickup_details=pickup_details,
                scheduled_pickup_at=scheduled_pickup_at,
                confirmed_at=timezone.now(),
                confirm_idempotency_key=idempotency_key,
            )
    except IntegrityError as exc:
        raise ConflictError('This request already has a confirmed trip.') from exc
    record_status_event(trip, '', trip.status, actor)

    previous = interest.status
    interest.status = DriverInterest.Status.SELECTED
    interest.save(update_fields=['status', 'modified_at'])
    record_status_event(interest, previous, interest.status, actor)

    _transition(trip_request, TripRequest.Status.CONFIRMED, actor)
    _decline_live_interests(trip_request, actor, 'INTEREST_NOT_SELECTED')
    create_notification(driver, 'TRIP_CONFIRMED', related_object_id=trip.pk, dedupe_key=f'TRIP_CONFIRMED:{trip.pk}')
    return trip, True


def _notify_matching_drivers(trip_request_id):
    from apps.matching.tasks import notify_matching_drivers

    try:
        notify_matching_drivers.delay(trip_request_id)
    except Exception:  # alerts are best-effort and must not break request creation
        pass


def _lock_trip(trip):
    return Trip.objects.select_for_update().select_related('trip_request__customer', 'driver').get(pk=trip.pk)


def _transition_trip(trip, to_status, actor, timestamp_field):
    if to_status not in TRIP_TRANSITIONS[trip.status]:
        raise ConflictError(f'Cannot change a {trip.status} trip to {to_status}.')
    previous = trip.status
    trip.status = to_status
    setattr(trip, timestamp_field, timezone.now())
    trip.save(update_fields=['status', timestamp_field, 'modified_at'])
    record_status_event(trip, previous, to_status, actor)


def _other_party(trip, actor):
    return trip.trip_request.customer if actor.pk == trip.driver_id else trip.driver


def _ensure_party(trip, actor):
    if actor.pk not in (trip.driver_id, trip.trip_request.customer_id):
        raise BusinessRuleError('You are not part of this trip.')


@transaction.atomic
def start_trip(trip, actor):
    """Only the driver starts a trip, and only from CONFIRMED."""
    trip = _lock_trip(trip)
    if actor.pk != trip.driver_id:
        raise BusinessRuleError('Only the driver can start the trip.')
    _transition_trip(trip, Trip.Status.IN_PROGRESS, actor, 'started_at')
    create_notification(
        trip.trip_request.customer, 'TRIP_STARTED', related_object_id=trip.pk, dedupe_key=f'TRIP_STARTED:{trip.pk}'
    )
    return trip


@transaction.atomic
def complete_trip(trip, actor):
    """Either party can close a trip that is IN_PROGRESS, so a forgetful driver cannot leave it open."""
    trip = _lock_trip(trip)
    _ensure_party(trip, actor)
    _transition_trip(trip, Trip.Status.COMPLETED, actor, 'completed_at')
    create_notification(
        _other_party(trip, actor), 'TRIP_COMPLETED', related_object_id=trip.pk, dedupe_key=f'TRIP_COMPLETED:{trip.pk}'
    )
    return trip


@transaction.atomic
def cancel_trip(trip, actor):
    """Either party may cancel before the trip starts. Once started, only support/admin can intervene."""
    trip = _lock_trip(trip)
    _ensure_party(trip, actor)
    if trip.status == Trip.Status.IN_PROGRESS:
        raise ConflictError('A trip in progress cannot be cancelled. Report a problem instead.')
    _transition_trip(trip, Trip.Status.CANCELLED, actor, 'cancelled_at')
    create_notification(
        _other_party(trip, actor), 'TRIP_CANCELLED', related_object_id=trip.pk, dedupe_key=f'TRIP_CANCELLED:{trip.pk}'
    )
    return trip


def remind_expiring_requests(now=None):
    """Tell customers once that their OPEN request is about to expire. Idempotent via the dedupe key."""
    now = now or timezone.now()
    horizon = now + timedelta(minutes=settings.REQUEST_REMINDER_MINUTES)
    count = 0
    for req in TripRequest.objects.filter(
        status=TripRequest.Status.OPEN, expires_at__gt=now, expires_at__lte=horizon
    ).select_related('customer'):
        key = f'REQUEST_EXPIRING:{req.pk}'
        if Notification.objects.filter(dedupe_key=key).exists():
            continue
        create_notification(req.customer, 'REQUEST_EXPIRING', related_object_id=req.pk, dedupe_key=key)
        count += 1
    return count

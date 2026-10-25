from django.conf import settings
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from apps.accounts.models import DriverProfile, User
from apps.areas.models import AreaCompatibility
from apps.notifications.services import create_notification
from apps.trips.models import DriverInterest, StatusEvent, Trip, TripRequest
from apps.trips.services import LIVE_INTEREST_STATUSES, record_status_event
from common.exceptions import BusinessRuleError, ConflictError
from common.geo import haversine_km

ACTIVE_TRIP_STATUSES = (Trip.Status.CONFIRMED, Trip.Status.IN_PROGRESS)


def location_is_fresh(profile, now=None):
    now = now or timezone.now()
    if profile.location_updated_at is None:
        return False
    return (now - profile.location_updated_at).total_seconds() <= settings.DRIVER_LOCATION_STALE_SECONDS


def destination_is_active(profile, now=None):
    now = now or timezone.now()
    return (
        profile.destination_area_id is not None
        and profile.destination_expires_at is not None
        and profile.destination_expires_at > now
    )


def driver_is_eligible(profile, now=None):
    """Request-independent candidate rules 1, 2, 3 and 6, plus a live destination (rule 5 needs one)."""
    now = now or timezone.now()
    user = profile.user
    return (
        user.is_driver  # rule 1: allowed to use the service
        and user.account_status == User.AccountStatus.ACTIVE
        and user.deleted_at is None
        and profile.availability_status == DriverProfile.Availability.AVAILABLE  # rule 2
        and location_is_fresh(profile, now)  # rule 3
        and destination_is_active(profile, now)
        and _has_capacity(user)  # rule 6
    )


def _has_capacity(user):
    return Trip.objects.filter(driver=user, status__in=ACTIVE_TRIP_STATUSES).count() < settings.DRIVER_MAX_ACTIVE_TRIPS


def is_near_pickup(profile, trip_request):
    """Rule 4. Precise coordinates on both sides win; otherwise the driver must be in the pickup area."""
    if (
        trip_request.pickup_latitude is not None
        and trip_request.pickup_longitude is not None
        and profile.current_latitude is not None
        and profile.current_longitude is not None
    ):
        distance = haversine_km(
            float(profile.current_latitude),
            float(profile.current_longitude),
            float(trip_request.pickup_latitude),
            float(trip_request.pickup_longitude),
        )
        return distance <= settings.DRIVER_MATCH_RADIUS_KM
    return profile.current_area_id is not None and profile.current_area_id == trip_request.pickup_area_id


def is_destination_compatible(profile, trip_request):
    """Rule 5: same destination, or a configured rule saying the request's destination is on the driver's way."""
    if profile.destination_area_id == trip_request.destination_area_id:
        return True
    return AreaCompatibility.objects.filter(
        origin_id=trip_request.pickup_area_id,
        driver_destination_id=profile.destination_area_id,
        request_destination_id=trip_request.destination_area_id,
    ).exists()


def is_candidate(profile, trip_request, now=None):
    """All seven candidate rules (business doc section 8) for one driver/request pair."""
    now = now or timezone.now()
    return (
        trip_request.status == TripRequest.Status.OPEN  # rule 7
        and trip_request.expires_at > now
        and trip_request.customer_id != profile.user_id
        and driver_is_eligible(profile, now)
        and is_near_pickup(profile, trip_request)
        and is_destination_compatible(profile, trip_request)
    )


def matching_requests(driver, now=None):
    """OPEN, unexpired requests that are candidates for `driver`. Matches are estimates, never guarantees."""
    now = now or timezone.now()
    profile = DriverProfile.objects.select_related('user').filter(user=driver).first()
    if profile is None or not driver_is_eligible(profile, now):
        return []

    compatible = AreaCompatibility.objects.filter(
        origin=OuterRef('pickup_area'),
        driver_destination=profile.destination_area_id,
        request_destination=OuterRef('destination_area'),
    )
    requests = (
        TripRequest.objects.filter(status=TripRequest.Status.OPEN, expires_at__gt=now)
        .exclude(customer=driver)
        .filter(Q(destination_area=profile.destination_area_id) | Exists(compatible))
        .select_related('pickup_area', 'destination_area')
    )
    return [r for r in requests if is_near_pickup(profile, r)]


REOPENABLE_INTEREST_STATUSES = (DriverInterest.Status.WITHDRAWN, DriverInterest.Status.DECLINED)


@transaction.atomic
def express_interest(driver, trip_request_id):
    """Idempotently mark `driver` as interested. Only candidates may, and only while the request is open."""
    trip_request = TripRequest.objects.select_for_update().filter(pk=trip_request_id).first()
    if trip_request is None:
        raise BusinessRuleError('Request not found.')
    now = timezone.now()
    if trip_request.status != TripRequest.Status.OPEN or trip_request.expires_at <= now:
        raise ConflictError('This request is closed.')
    profile = DriverProfile.objects.select_related('user').filter(user=driver).first()
    if profile is None or not is_candidate(profile, trip_request, now):
        raise BusinessRuleError('This request does not match your trip.')

    interest, created = DriverInterest.objects.select_for_update().get_or_create(
        trip_request=trip_request, driver=driver
    )
    if not created:
        if interest.status in LIVE_INTEREST_STATUSES:
            return interest, False
        if interest.status not in REOPENABLE_INTEREST_STATUSES:
            raise ConflictError('Your interest can no longer be changed.')
        previous = interest.status
        interest.status = DriverInterest.Status.INTERESTED
        interest.save(update_fields=['status', 'modified_at'])
        record_status_event(interest, previous, interest.status, driver)
    else:
        record_status_event(interest, '', interest.status, driver)

    events = StatusEvent.objects.filter(object_type='DriverInterest', object_id=interest.pk).count()
    create_notification(
        trip_request.customer,
        'DRIVER_INTERESTED',
        related_object_id=trip_request.pk,
        dedupe_key=f'DRIVER_INTERESTED:{interest.pk}:{events}',
    )
    return interest, True


@transaction.atomic
def withdraw_interest(driver, trip_request_id):
    """Idempotently withdraw interest before the trip is confirmed."""
    trip_request = TripRequest.objects.select_for_update().filter(pk=trip_request_id).first()
    interest = (
        DriverInterest.objects.select_for_update().filter(trip_request=trip_request, driver=driver).first()
        if trip_request
        else None
    )
    if interest is None:
        raise BusinessRuleError('You have not shown interest in this request.')
    if interest.status == DriverInterest.Status.SELECTED:
        raise ConflictError('You were already selected for this request.')
    if interest.status in LIVE_INTEREST_STATUSES:
        previous = interest.status
        interest.status = DriverInterest.Status.WITHDRAWN
        interest.save(update_fields=['status', 'modified_at'])
        record_status_event(interest, previous, interest.status, driver)
    return interest


def notify_matching_drivers(trip_request_id):
    """Alert available drivers for whom a new request is a candidate. One alert per driver and request."""
    trip_request = TripRequest.objects.filter(pk=trip_request_id).first()
    if trip_request is None:
        return 0
    now = timezone.now()
    notified = 0
    profiles = DriverProfile.objects.select_related('user').filter(
        availability_status=DriverProfile.Availability.AVAILABLE
    )
    for profile in profiles:
        if is_candidate(profile, trip_request, now):
            create_notification(
                profile.user,
                'NEW_MATCHING_REQUEST',
                related_object_id=trip_request.pk,
                dedupe_key=f'NEW_MATCHING_REQUEST:{trip_request.pk}:{profile.user_id}',
            )
            notified += 1
    return notified


import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.trips.models import DriverInterest, StatusEvent, Trip, TripRequest
from apps.trips.services import record_status_event


def test_request_defaults_to_open(trip_request):
    assert trip_request.status == TripRequest.Status.OPEN


def test_request_rejects_same_pickup_and_destination(customer, areas):
    with pytest.raises(IntegrityError), transaction.atomic():
        TripRequest.objects.create(
            customer=customer,
            pickup_area=areas['محطة'],
            destination_area=areas['محطة'],
            expires_at=timezone.now(),
        )


def test_interest_is_unique_per_request_and_driver(trip_request, driver):
    DriverInterest.objects.create(trip_request=trip_request, driver=driver)
    with pytest.raises(IntegrityError), transaction.atomic():
        DriverInterest.objects.create(trip_request=trip_request, driver=driver)


def test_only_one_active_trip_per_request(trip_request, driver, make_user):
    Trip.objects.create(trip_request=trip_request, driver=driver)
    with pytest.raises(IntegrityError), transaction.atomic():
        Trip.objects.create(trip_request=trip_request, driver=make_user(is_driver=True))


def test_new_trip_allowed_after_previous_is_cancelled(trip_request, driver, make_user):
    first = Trip.objects.create(trip_request=trip_request, driver=driver)
    first.status = Trip.Status.CANCELLED
    first.save()
    Trip.objects.create(trip_request=trip_request, driver=make_user(is_driver=True))
    assert Trip.objects.filter(trip_request=trip_request).count() == 2


def test_record_status_event_appends_log(trip_request, customer):
    record_status_event(trip_request, 'OPEN', 'CANCELLED', actor=customer)
    event = StatusEvent.objects.get()
    assert (event.object_type, event.object_id) == ('TripRequest', trip_request.pk)
    assert (event.from_status, event.to_status, event.actor) == ('OPEN', 'CANCELLED', customer)

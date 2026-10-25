from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.matching import services
from apps.trips.models import Trip, TripRequest


def ids(driver):
    return [r.pk for r in services.matching_requests(driver.user)]


def test_same_destination_matches(make_driver, trip_request):
    assert ids(make_driver()) == [trip_request.pk]


def test_example_driver_to_alt_destination_needs_compat_rule(make_driver, make_request, areas, compat):
    # Business doc §8 example 2: station -> معلمين request, driver heads to الأربعين.
    request = make_request(destination_area=areas['معلمين'])
    assert ids(make_driver()) == [request.pk]


def test_example_alt_destination_without_rule_does_not_match(make_driver, make_request, areas):
    make_request(destination_area=areas['معلمين'])
    assert ids(make_driver()) == []


def test_example_opposite_direction_does_not_match(make_driver, make_request, areas):
    # Business doc §8 example 3: driver in الأربعين heading to المحطة, request to الأربعين.
    make_request(pickup_area=areas['محطة'], destination_area=areas['أربعين'])
    driver = make_driver(current_area=areas['أربعين'], destination_area=areas['محطة'])
    assert ids(driver) == []


@pytest.mark.parametrize(
    'override',
    [
        {'availability_status': 'OFFLINE'},
        {'location_updated_at': None},
        {'location_updated_at': timezone.now() - timedelta(hours=1)},
        {'destination_area': None, 'destination_expires_at': None},
        {'destination_expires_at': timezone.now() - timedelta(minutes=1)},
    ],
)
def test_ineligible_drivers_see_nothing(make_driver, trip_request, override):
    assert ids(make_driver(**override)) == []


def test_suspended_driver_sees_nothing(make_driver, trip_request):
    driver = make_driver()
    driver.user.account_status = 'SUSPENDED'
    driver.user.save()
    assert ids(driver) == []


@pytest.mark.parametrize('status', ['CONFIRMED', 'CANCELLED', 'EXPIRED'])
def test_closed_requests_hidden(make_driver, make_request, status):
    make_request(status=status)
    assert ids(make_driver()) == []


def test_expired_by_time_request_hidden(make_driver, make_request):
    make_request(expires_at=timezone.now() - timedelta(seconds=1))
    assert ids(make_driver()) == []


def test_driver_does_not_see_own_request(make_driver, make_request):
    driver = make_driver()
    make_request(customer=driver.user)
    assert ids(driver) == []


def test_other_pickup_area_hidden(make_driver, make_request, areas):
    make_request(pickup_area=areas['معلمين'])
    assert ids(make_driver()) == []


def test_precise_coordinates_use_radius(make_driver, make_request, settings):
    settings.DRIVER_MATCH_RADIUS_KM = 2
    driver = make_driver(current_latitude=Decimal('30.000000'), current_longitude=Decimal('32.000000'))
    near = make_request(pickup_latitude=Decimal('30.005'), pickup_longitude=Decimal('32.000'))
    make_request(pickup_latitude=Decimal('30.100'), pickup_longitude=Decimal('32.000'))
    assert ids(driver) == [near.pk]


def test_capacity_rule_blocks_driver_with_active_trip(make_driver, make_request, trip_request):
    driver = make_driver()
    other = make_request(status=TripRequest.Status.CONFIRMED)
    Trip.objects.create(trip_request=other, driver=driver.user, status=Trip.Status.CONFIRMED)
    assert ids(driver) == []


def test_capacity_configurable(make_driver, make_request, trip_request, settings):
    settings.DRIVER_MAX_ACTIVE_TRIPS = 2
    driver = make_driver()
    other = make_request(status=TripRequest.Status.CONFIRMED)
    Trip.objects.create(trip_request=other, driver=driver.user, status=Trip.Status.IN_PROGRESS)
    assert ids(driver) == [trip_request.pk]


def test_completed_trip_does_not_block(make_driver, make_request, trip_request):
    driver = make_driver()
    done = make_request(status=TripRequest.Status.CONFIRMED)
    Trip.objects.create(trip_request=done, driver=driver.user, status=Trip.Status.COMPLETED)
    assert ids(driver) == [trip_request.pk]

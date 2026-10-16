from datetime import timedelta

import pytest
from django.utils import timezone

from apps.trips.models import DriverInterest, TripRequest


@pytest.fixture
def make_request(customer, areas):
    def _make(**extra):
        defaults = {
            'customer': customer,
            'pickup_area': areas['محطة'],
            'destination_area': areas['أربعين'],
            'expires_at': timezone.now() + timedelta(minutes=30),
        }
        return TripRequest.objects.create(**{**defaults, **extra})

    return _make


@pytest.fixture
def trip_request(make_request):
    return make_request()


@pytest.fixture
def make_interest(make_user):
    def _make(trip_request, status=DriverInterest.Status.INTERESTED):
        return DriverInterest.objects.create(trip_request=trip_request, driver=make_user(is_driver=True), status=status)

    return _make

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import DriverProfile
from apps.areas.models import AreaCompatibility


@pytest.fixture
def make_driver(make_user, areas):
    """An eligible driver: available, fresh location in the station, heading to الأربعين."""

    def _make(**profile_overrides):
        user = make_user(is_driver=True)
        fields = {
            'availability_status': DriverProfile.Availability.AVAILABLE,
            'current_area': areas['محطة'],
            'destination_area': areas['أربعين'],
            'destination_expires_at': timezone.now() + timedelta(hours=1),
            'location_updated_at': timezone.now(),
        }
        fields.update(profile_overrides)
        return DriverProfile.objects.create(user=user, **fields)

    return _make


@pytest.fixture
def compat(areas):
    return AreaCompatibility.objects.create(
        origin=areas['محطة'], driver_destination=areas['أربعين'], request_destination=areas['معلمين']
    )

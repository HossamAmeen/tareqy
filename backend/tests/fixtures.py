from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle


@pytest.fixture(autouse=True)
def _isolated_state(settings, monkeypatch):
    from apps.accounts.sms import LocMemSMSBackend

    settings.SMS_BACKEND = 'apps.accounts.sms.LocMemSMSBackend'
    LocMemSMSBackend.outbox.clear()
    """Isolated cache, deterministic secrets and generous default throttle rates."""
    settings.HEALTH_CHECK_PASSWORD = 'test-health-secret'
    settings.DRIVER_VERIFICATION_REQUIRED = False
    settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    monkeypatch.setattr(
        SimpleRateThrottle,
        'THROTTLE_RATES',
        {
            'anon': '1000/minute',
            'user': '1000/minute',
            'auth': '1000/minute',
            'sensitive': '1000/minute',
            'health': '1000/minute',
            'location': '1000/minute',
        },
    )
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sms_outbox():
    from apps.accounts.sms import LocMemSMSBackend

    return LocMemSMSBackend.outbox


@pytest.fixture
def make_user(db, django_user_model):
    counter = iter(range(1, 10_000))

    def _make(**extra):
        extra.setdefault('phone', f'+2010000{next(counter):05d}')
        return django_user_model.objects.create_user(**extra)

    return _make


@pytest.fixture
def customer(make_user):
    return make_user(name='Customer')


@pytest.fixture
def driver(make_user):
    return make_user(name='Driver', is_driver=True)


@pytest.fixture
def staff(make_user):
    return make_user(is_staff=True)


@pytest.fixture
def auth_client(api_client):
    def _auth(user):
        api_client.force_authenticate(user)
        return api_client

    return _auth


@pytest.fixture
def areas(db):
    from apps.areas.models import Area

    return {n: Area.objects.create(name=n) for n in ['محطة', 'أربعين', 'معلمين']}


@pytest.fixture
def make_request(customer, areas):
    from apps.trips.models import TripRequest

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
    from apps.trips.models import DriverInterest

    def _make(trip_request, status='INTERESTED'):
        return DriverInterest.objects.create(trip_request=trip_request, driver=make_user(is_driver=True), status=status)

    return _make

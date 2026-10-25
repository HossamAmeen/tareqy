import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.urls import reverse

from apps.trips import services
from common.logging import RedactPhoneFilter

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def trip(customer, trip_request, make_interest):
    return services.confirm_trip(trip_request, customer, interest_id=make_interest(trip_request).pk, agreed_price='5')[
        0
    ]


def test_object_level_access_is_denied_across_users(auth_client, make_user, trip, trip_request):
    """A user who is not part of the request/trip cannot read or act on it (404, never 200/403 leaks)."""
    outsider = auth_client(make_user())
    probes = [
        ('get', reverse('request-detail', args=[trip_request.pk])),
        ('patch', reverse('request-detail', args=[trip_request.pk])),
        ('post', reverse('request-cancel', args=[trip_request.pk])),
        ('get', reverse('request-interests', args=[trip_request.pk])),
        ('post', reverse('request-confirm', args=[trip_request.pk])),
        ('get', reverse('trip-detail', args=[trip.pk])),
        ('post', reverse('trip-start', args=[trip.pk])),
        ('post', reverse('trip-complete', args=[trip.pk])),
        ('post', reverse('trip-cancel', args=[trip.pk])),
    ]
    for method, url in probes:
        assert getattr(outsider, method)(url, {}, format='json').status_code == 404, (method, url)


def test_phone_numbers_only_appear_to_the_trip_parties(auth_client, make_user, customer, trip):
    outsider = make_user(is_driver=True)
    client = auth_client(outsider)
    body = ''.join(
        client.get(reverse(name)).content.decode()
        for name in ('driver-interests', 'trip-list', 'request-list', 'notification-list')
    )
    assert customer.phone not in body and trip.driver.phone not in body


def test_staff_endpoints_reject_regular_roles(auth_client, trip):
    for user in (trip.driver, trip.trip_request.customer):
        client = auth_client(user)
        assert client.get(reverse('admin-user-list')).status_code == 403
        assert client.post(reverse('admin-user-suspend', args=[user.pk])).status_code == 403


def test_logging_filter_redacts_phone_numbers():
    record = logging.LogRecord('x', logging.WARNING, __file__, 1, 'SMS to %s failed', ('+201000000001',), None)
    RedactPhoneFilter().filter(record)
    assert '+2010' not in record.msg and '[phone]' in record.msg


def test_logging_filter_keeps_ordinary_messages():
    record = logging.LogRecord('x', logging.INFO, __file__, 1, 'Push to subscription %s failed', (42,), None)
    RedactPhoneFilter().filter(record)
    assert record.msg == 'Push to subscription 42 failed'


def _load_production(**env):
    base = {
        **os.environ,
        'DJANGO_SETTINGS_MODULE': 'config.settings.production',
        'SECRET_KEY': 'k' * 40,
        'SMS_BACKEND': 'apps.accounts.sms.LocMemSMSBackend',
        'CORS_ALLOWED_ORIGINS': 'https://app.example.com',
        **env,
    }
    return subprocess.run(
        [sys.executable, '-c', 'import django.conf; django.conf.settings.SECRET_KEY'],
        cwd=BACKEND_DIR,
        env=base,
        capture_output=True,
        text=True,
    )


def test_production_settings_accept_safe_configuration():
    assert _load_production().returncode == 0


@pytest.mark.parametrize(
    'override',
    [
        {'SECRET_KEY': 'short'},
        {'SMS_BACKEND': 'apps.accounts.sms.ConsoleSMSBackend'},
        {'CORS_ALLOWED_ORIGINS': 'http://localhost:5173'},
    ],
)
def test_production_settings_refuse_unsafe_configuration(override):
    result = _load_production(**override)
    assert result.returncode != 0 and 'ImproperlyConfigured' in result.stderr

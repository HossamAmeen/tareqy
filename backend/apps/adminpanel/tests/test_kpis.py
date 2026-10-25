from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import DriverProfile
from apps.adminpanel.kpis import compute_kpis
from apps.trips import services
from apps.trips.models import DriverInterest, Trip, TripRequest


def test_empty_window_returns_none_rates(db):
    kpis = compute_kpis()
    assert kpis['requests_published'] == 0
    assert kpis['confirmation_rate'] is None and kpis['avg_seconds_to_confirmation'] is None


@pytest.fixture
def scenario(customer, make_request, make_user, make_interest):
    """5 requests: 1 confirmed (with interest), 1 cancelled, 1 expired by time, 1 open, 1 open with interest."""
    base = timezone.now() - timedelta(hours=1)
    confirmed = make_request()
    TripRequest.objects.filter(pk=confirmed.pk).update(created_at=base)
    interest = make_interest(confirmed)
    DriverInterest.objects.filter(pk=interest.pk).update(created_at=base + timedelta(seconds=60))
    trip, _ = services.confirm_trip(confirmed, customer, interest_id=interest.pk, agreed_price='5')
    Trip.objects.filter(pk=trip.pk).update(confirmed_at=base + timedelta(seconds=300))
    make_request(status='CANCELLED')
    make_request(expires_at=timezone.now() - timedelta(minutes=1))
    make_request()
    other = make_request()
    DriverInterest.objects.filter(pk=make_interest(other).pk).update(
        created_at=other.created_at + timedelta(seconds=60)
    )
    return confirmed


def test_rates_and_times(scenario):
    kpis = compute_kpis()
    assert kpis['requests_published'] == 5
    assert kpis['open_now'] == 2
    # decided = confirmed + cancelled + expired = 3
    assert kpis['confirmation_rate'] == pytest.approx(1 / 3, abs=1e-4)
    assert kpis['expired_rate'] == pytest.approx(1 / 3, abs=1e-4)
    assert kpis['cancelled_before_confirmation_rate'] == pytest.approx(1 / 3, abs=1e-4)
    assert kpis['interest_rate'] == pytest.approx(2 / 5, abs=1e-4)
    assert kpis['avg_seconds_to_first_interest'] == 60
    assert kpis['avg_seconds_to_confirmation'] == 300
    assert kpis['cancelled_after_confirmation_rate'] == 0
    assert sum(d['count'] for d in kpis['requests_per_day']) == 5


def test_cancellation_after_confirmation(scenario, customer):
    trip = Trip.objects.get()
    services.cancel_trip(trip, customer)
    assert compute_kpis()['cancelled_after_confirmation_rate'] == 1


def test_test_accounts_are_excluded_unless_requested(scenario, customer):
    customer.is_test_account = True
    customer.save()
    assert compute_kpis()['requests_published'] == 0
    assert compute_kpis(include_test=True)['requests_published'] == 5


def test_window_excludes_old_requests(scenario):
    TripRequest.objects.update(created_at=timezone.now() - timedelta(days=40))
    assert compute_kpis(days=30)['requests_published'] == 0
    assert compute_kpis(days=60)['requests_published'] == 5


def test_returning_customers(make_user, make_request):
    a, b = make_user(), make_user()
    make_request(customer=a)
    make_request(customer=a)
    make_request(customer=b)
    kpis = compute_kpis()
    assert (kpis['customers'], kpis['returning_customers'], kpis['returning_customer_rate']) == (2, 1, 0.5)


def test_active_drivers_counts_recent_locations(make_user):
    for hours in (1, 30):
        DriverProfile.objects.create(
            user=make_user(is_driver=True), location_updated_at=timezone.now() - timedelta(hours=hours)
        )
    assert compute_kpis()['active_drivers_24h'] == 1


def test_endpoint_params(auth_client, staff, scenario):
    client = auth_client(staff)
    data = client.get(reverse('admin-kpis'), {'days': 'abc'}).json()['data']
    assert data['window_days'] == 30
    assert client.get(reverse('admin-kpis'), {'days': 9999}).json()['data']['window_days'] == 365
    assert client.get(reverse('admin-kpis'), {'include_test': 'true'}).json()['data']['include_test'] is True

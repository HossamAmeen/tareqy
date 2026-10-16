import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.notifications.models import Notification
from apps.trips import services
from apps.trips.models import DriverInterest, StatusEvent, TripRequest
from common.exceptions import BusinessRuleError, ConflictError


def test_create_request_sets_open_status_and_expiry(customer, areas, settings):
    settings.REQUEST_TTL_MINUTES = 10
    before = timezone.now()
    req = services.create_request(customer, pickup_area=areas['محطة'], destination_area=areas['أربعين'])
    assert req.status == TripRequest.Status.OPEN
    assert before + timedelta(minutes=9) < req.expires_at < before + timedelta(minutes=11)
    event = StatusEvent.objects.get(object_type='TripRequest', object_id=req.pk)
    assert (event.from_status, event.to_status, event.actor) == ('', 'OPEN', customer)


def test_create_request_rejects_same_areas(customer, areas):
    with pytest.raises(BusinessRuleError):
        services.create_request(customer, pickup_area=areas['محطة'], destination_area=areas['محطة'])


def test_create_request_rejects_inactive_area(customer, areas):
    areas['أربعين'].is_active = False
    areas['أربعين'].save()
    with pytest.raises(BusinessRuleError):
        services.create_request(customer, pickup_area=areas['محطة'], destination_area=areas['أربعين'])


def test_create_request_rejects_past_preferred_time(customer, areas):
    with pytest.raises(BusinessRuleError):
        services.create_request(
            customer,
            pickup_area=areas['محطة'],
            destination_area=areas['أربعين'],
            preferred_pickup_at=timezone.now() - timedelta(minutes=1),
        )


def test_create_request_requires_customer_role(make_user, areas):
    only_driver = make_user(is_customer=False, is_driver=True)
    with pytest.raises(BusinessRuleError):
        services.create_request(only_driver, pickup_area=areas['محطة'], destination_area=areas['أربعين'])


def test_cancel_open_request(trip_request, customer, make_interest):
    interest = make_interest(trip_request)
    services.cancel_request(trip_request, customer)
    trip_request.refresh_from_db()
    interest.refresh_from_db()
    assert trip_request.status == TripRequest.Status.CANCELLED
    assert interest.status == DriverInterest.Status.DECLINED
    assert Notification.objects.filter(user=interest.driver, type='REQUEST_CANCELLED').count() == 1


@pytest.mark.parametrize('status', ['CANCELLED', 'CONFIRMED', 'EXPIRED'])
def test_cannot_cancel_closed_request(make_request, customer, status):
    req = make_request(status=status)
    with pytest.raises(ConflictError):
        services.cancel_request(req, customer)


def test_cannot_cancel_past_expiry(make_request, customer):
    req = make_request(expires_at=timezone.now() - timedelta(seconds=1))
    with pytest.raises(ConflictError):
        services.cancel_request(req, customer)


def test_update_notes_keeps_interests(trip_request, customer, make_interest):
    interest = make_interest(trip_request)
    services.update_request(trip_request, customer, notes='Near the gate')
    interest.refresh_from_db()
    assert interest.status == DriverInterest.Status.INTERESTED
    assert not Notification.objects.exists()


def test_substantial_update_declines_interests_and_notifies(trip_request, customer, areas, make_interest):
    kept = make_interest(trip_request, DriverInterest.Status.CONTACTED)
    withdrawn = make_interest(trip_request, DriverInterest.Status.WITHDRAWN)
    services.update_request(trip_request, customer, destination_area=areas['معلمين'])
    kept.refresh_from_db()
    withdrawn.refresh_from_db()
    assert kept.status == DriverInterest.Status.DECLINED
    assert withdrawn.status == DriverInterest.Status.WITHDRAWN
    assert Notification.objects.filter(type='REQUEST_CHANGED').count() == 1
    assert StatusEvent.objects.filter(object_type='DriverInterest', object_id=kept.pk, to_status='DECLINED').exists()


def test_substantial_update_clears_stale_precise_location(make_request, customer, areas):
    req = make_request(pickup_latitude='30.1', pickup_longitude='32.5')
    services.update_request(req, customer, pickup_area=areas['معلمين'])
    req.refresh_from_db()
    assert req.pickup_latitude is None and req.pickup_longitude is None


def test_update_to_same_areas_is_rejected(trip_request, customer, areas):
    with pytest.raises(BusinessRuleError):
        services.update_request(trip_request, customer, destination_area=areas['محطة'])


@pytest.mark.parametrize('status', ['CANCELLED', 'CONFIRMED', 'EXPIRED'])
def test_cannot_update_closed_request(make_request, customer, status):
    with pytest.raises(ConflictError):
        services.update_request(make_request(status=status), customer, notes='x')


def test_cannot_update_after_expiry(make_request, customer):
    req = make_request(expires_at=timezone.now() - timedelta(seconds=1))
    with pytest.raises(ConflictError):
        services.update_request(req, customer, notes='x')


def test_expire_due_requests_only_touches_due_open_requests(make_request, make_interest):
    due = make_request(expires_at=timezone.now() - timedelta(minutes=1))
    interest = make_interest(due)
    fresh = make_request()
    confirmed = make_request(status='CONFIRMED', expires_at=timezone.now() - timedelta(minutes=1))

    assert services.expire_due_requests() == 1
    for obj in (due, fresh, confirmed, interest):
        obj.refresh_from_db()
    assert due.status == 'EXPIRED' and fresh.status == 'OPEN' and confirmed.status == 'CONFIRMED'
    assert interest.status == 'DECLINED'
    assert StatusEvent.objects.filter(object_type='TripRequest', object_id=due.pk, to_status='EXPIRED').exists()


def test_expire_due_requests_is_idempotent(make_request):
    make_request(expires_at=timezone.now() - timedelta(minutes=1))
    assert services.expire_due_requests() == 1
    assert services.expire_due_requests() == 0
    assert Notification.objects.count() == 0


def test_effective_status_reads_expired_before_job_runs(make_request):
    req = make_request(expires_at=timezone.now() - timedelta(seconds=1))
    assert req.status == 'OPEN' and req.effective_status == 'EXPIRED'


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor == 'sqlite', reason='needs row locks (PostgreSQL)')
def test_concurrent_cancel_and_update_leave_consistent_state(make_user, areas):
    customer = make_user()
    req = services.create_request(customer, pickup_area=areas['محطة'], destination_area=areas['أربعين'])
    results = []

    def cancel():
        try:
            services.cancel_request(req, customer)
            results.append('ok')
        except ConflictError:
            results.append('conflict')

    threads = [threading.Thread(target=cancel) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == ['conflict', 'ok']

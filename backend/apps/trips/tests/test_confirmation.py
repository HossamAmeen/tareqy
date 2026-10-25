import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import DriverProfile
from apps.notifications.models import Notification
from apps.trips import services
from apps.trips.models import DriverInterest, StatusEvent, Trip, TripRequest
from common.exceptions import BusinessRuleError, ConflictError


@pytest.fixture
def interest(make_interest, trip_request):
    return make_interest(trip_request)


def confirm(trip_request, customer, interest, **extra):
    kwargs = {'interest_id': interest.pk, 'agreed_price': '50.00', **extra}
    return services.confirm_trip(trip_request, customer, **kwargs)


# --- service ---


def test_confirm_links_one_driver_and_closes_the_rest(customer, trip_request, make_interest, interest):
    other = make_interest(trip_request)
    contacted = make_interest(trip_request, status=DriverInterest.Status.CONTACTED)
    withdrawn = make_interest(trip_request, status=DriverInterest.Status.WITHDRAWN)

    trip, created = confirm(trip_request, customer, interest, pickup_details='Gate 2')

    assert created
    trip.refresh_from_db()
    assert trip.status == Trip.Status.CONFIRMED and trip.driver == interest.driver
    assert trip.agreed_price == 50 and trip.confirmed_at is not None
    for obj in (trip_request, interest, other, contacted, withdrawn):
        obj.refresh_from_db()
    assert trip_request.status == TripRequest.Status.CONFIRMED
    assert interest.status == 'SELECTED'
    assert other.status == contacted.status == 'DECLINED'
    assert withdrawn.status == 'WITHDRAWN'
    assert StatusEvent.objects.filter(object_type='Trip', object_id=trip.pk, to_status='CONFIRMED').exists()
    assert Notification.objects.filter(user=interest.driver, type='TRIP_CONFIRMED').count() == 1
    assert Notification.objects.filter(user=other.driver, type='INTEREST_NOT_SELECTED').count() == 1


@pytest.mark.parametrize('status', ['CANCELLED', 'EXPIRED', 'CONFIRMED'])
def test_confirm_rejects_closed_request(customer, make_request, make_interest, status):
    request = make_request(status=status)
    interest = make_interest(request)
    with pytest.raises(ConflictError):
        confirm(request, customer, interest)
    assert not Trip.objects.exists()


def test_confirm_rejects_time_expired_request(customer, make_request, make_interest):
    request = make_request(expires_at=timezone.now() - timedelta(seconds=1))
    with pytest.raises(ConflictError):
        confirm(request, customer, make_interest(request))
    assert not Trip.objects.exists()


@pytest.mark.parametrize('status', ['WITHDRAWN', 'DECLINED'])
def test_confirm_rejects_dead_interest(customer, trip_request, make_interest, status):
    with pytest.raises(ConflictError):
        confirm(trip_request, customer, make_interest(trip_request, status=status))


def test_confirm_rejects_interest_of_another_request(customer, trip_request, make_request, make_interest):
    foreign = make_interest(make_request())
    with pytest.raises(BusinessRuleError):
        confirm(trip_request, customer, foreign)


def test_confirm_rejects_past_pickup_time(customer, trip_request, interest):
    with pytest.raises(BusinessRuleError):
        confirm(trip_request, customer, interest, scheduled_pickup_at=timezone.now() - timedelta(minutes=1))


def test_driver_with_active_trip_conflicts(customer, trip_request, interest, make_request):
    Trip.objects.create(
        trip_request=make_request(status=TripRequest.Status.CONFIRMED), driver=interest.driver, status='IN_PROGRESS'
    )
    with pytest.raises(ConflictError):
        confirm(trip_request, customer, interest)
    trip_request.refresh_from_db()
    assert trip_request.status == TripRequest.Status.OPEN


def test_driver_capacity_is_configurable(customer, trip_request, interest, make_request, settings):
    settings.DRIVER_MAX_ACTIVE_TRIPS = 2
    Trip.objects.create(
        trip_request=make_request(status=TripRequest.Status.CONFIRMED), driver=interest.driver, status='CONFIRMED'
    )
    assert confirm(trip_request, customer, interest)[1]


def test_completed_trip_does_not_block_driver(customer, trip_request, interest, make_request):
    Trip.objects.create(
        trip_request=make_request(status=TripRequest.Status.CONFIRMED), driver=interest.driver, status='COMPLETED'
    )
    assert confirm(trip_request, customer, interest)[1]


def test_suspended_driver_cannot_be_confirmed(customer, trip_request, interest):
    interest.driver.account_status = 'SUSPENDED'
    interest.driver.save()
    with pytest.raises(ConflictError):
        confirm(trip_request, customer, interest)


def test_idempotent_retry_returns_same_trip(customer, trip_request, interest):
    first, created = confirm(trip_request, customer, interest, idempotency_key='k1')
    again, created_again = confirm(trip_request, customer, interest, idempotency_key='k1')
    assert created and not created_again
    assert first.pk == again.pk and Trip.objects.count() == 1
    assert Notification.objects.filter(type='TRIP_CONFIRMED').count() == 1


def test_different_key_after_confirmation_conflicts(customer, trip_request, interest):
    confirm(trip_request, customer, interest, idempotency_key='k1')
    with pytest.raises(ConflictError):
        confirm(trip_request, customer, interest, idempotency_key='k2')
    assert Trip.objects.count() == 1


def test_mark_contacted_is_idempotent(customer, trip_request, interest):
    assert services.mark_contacted(trip_request, interest.pk, customer).status == 'CONTACTED'
    assert services.mark_contacted(trip_request, interest.pk, customer).status == 'CONTACTED'
    assert Notification.objects.filter(type='CUSTOMER_CONTACTED').count() == 1


def test_mark_contacted_requires_live_interest(customer, trip_request, make_interest):
    dead = make_interest(trip_request, status='WITHDRAWN')
    with pytest.raises(ConflictError):
        services.mark_contacted(trip_request, dead.pk, customer)


# --- concurrency (PostgreSQL only: needs real row locks) ---

needs_postgres = pytest.mark.skipif(connection.vendor == 'sqlite', reason='needs row locks (PostgreSQL)')


def _run_parallel(targets):
    results = []

    def wrap(fn):
        def run():
            try:
                fn()
                results.append('ok')
            except ConflictError:
                results.append('conflict')
            finally:
                connection.close()

        return run

    threads = [threading.Thread(target=wrap(t)) for t in targets]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return sorted(results)


@pytest.mark.django_db(transaction=True)
@needs_postgres
def test_two_drivers_confirmed_at_once_exactly_one_wins(make_user, areas):
    customer = make_user()
    req = services.create_request(customer, pickup_area=areas['محطة'], destination_area=areas['أربعين'])
    interests = [DriverInterest.objects.create(trip_request=req, driver=make_user(is_driver=True)) for _ in range(2)]
    results = _run_parallel(
        [lambda i=i: services.confirm_trip(req, customer, interest_id=i.pk, agreed_price='10') for i in interests]
    )
    assert results == ['conflict', 'ok']
    assert Trip.objects.exclude(status='CANCELLED').count() == 1
    assert DriverInterest.objects.filter(status='SELECTED').count() == 1
    assert DriverInterest.objects.filter(status='DECLINED').count() == 1


@pytest.mark.django_db(transaction=True)
@needs_postgres
def test_same_confirmation_retried_in_parallel_creates_one_trip(make_user, areas):
    customer = make_user()
    req = services.create_request(customer, pickup_area=areas['محطة'], destination_area=areas['أربعين'])
    interest = DriverInterest.objects.create(trip_request=req, driver=make_user(is_driver=True))
    # Parallel retries with one key: nobody sees a conflict, every call returns the single trip.
    results = _run_parallel(
        [
            lambda: services.confirm_trip(
                req, customer, interest_id=interest.pk, agreed_price='10', idempotency_key='same'
            )
            for _ in range(3)
        ]
    )
    assert results == ['ok', 'ok', 'ok']
    assert Trip.objects.count() == 1


@pytest.mark.django_db(transaction=True)
@needs_postgres
def test_confirm_racing_with_cancel_has_one_winner(make_user, areas):
    customer = make_user()
    req = services.create_request(customer, pickup_area=areas['محطة'], destination_area=areas['أربعين'])
    interest = DriverInterest.objects.create(trip_request=req, driver=make_user(is_driver=True))
    results = _run_parallel(
        [
            lambda: services.confirm_trip(req, customer, interest_id=interest.pk, agreed_price='10'),
            lambda: services.cancel_request(req, customer),
        ]
    )
    assert results == ['conflict', 'ok']
    req.refresh_from_db()
    assert (req.status == 'CONFIRMED') == (Trip.objects.count() == 1)


@pytest.mark.django_db(transaction=True)
@needs_postgres
def test_confirm_racing_with_expiry_has_one_winner(make_user, areas):
    customer = make_user()
    req = services.create_request(customer, pickup_area=areas['محطة'], destination_area=areas['أربعين'])
    TripRequest.objects.filter(pk=req.pk).update(expires_at=timezone.now() + timedelta(milliseconds=300))
    interest = DriverInterest.objects.create(trip_request=req, driver=make_user(is_driver=True))
    import time

    time.sleep(0.35)
    with pytest.raises(ConflictError):
        services.confirm_trip(req, customer, interest_id=interest.pk, agreed_price='10')
    assert Trip.objects.count() == 0


@pytest.mark.django_db(transaction=True)
@needs_postgres
def test_one_driver_cannot_win_two_requests_at_once(make_user, areas):
    customer_a, customer_b, driver = make_user(), make_user(), make_user(is_driver=True)
    DriverProfile.objects.create(user=driver)
    reqs, interests = [], []
    for c in (customer_a, customer_b):
        r = services.create_request(c, pickup_area=areas['محطة'], destination_area=areas['أربعين'])
        reqs.append(r)
        interests.append(DriverInterest.objects.create(trip_request=r, driver=driver))
    results = _run_parallel(
        [
            lambda c=c, r=r, i=i: services.confirm_trip(r, c, interest_id=i.pk, agreed_price='10')
            for c, r, i in zip((customer_a, customer_b), reqs, interests, strict=True)
        ]
    )
    assert results == ['conflict', 'ok']
    assert Trip.objects.filter(driver=driver).count() == 1


# --- API ---


def confirm_url(req):
    return reverse('request-confirm', args=[req.pk])


def test_interests_list_reveals_driver_phone_only_for_live(auth_client, customer, trip_request, make_interest):
    live = make_interest(trip_request)
    make_interest(trip_request, status='WITHDRAWN')
    make_interest(trip_request, status='DECLINED')
    rows = auth_client(customer).get(reverse('request-interests', args=[trip_request.pk])).json()['data']
    assert [r['id'] for r in rows] == [live.pk]
    assert rows[0]['driver']['phone'] == live.driver.phone


def test_interests_hidden_from_other_customers(auth_client, make_user, trip_request, interest):
    other = make_user()
    assert auth_client(other).get(reverse('request-interests', args=[trip_request.pk])).status_code == 404


def test_contacted_endpoint(auth_client, customer, trip_request, interest):
    url = reverse('request-contacted', args=[trip_request.pk, interest.pk])
    assert auth_client(customer).post(url).json()['data']['status'] == 'CONTACTED'


def test_confirm_endpoint_and_idempotent_replay(auth_client, customer, trip_request, interest):
    client = auth_client(customer)
    body = {'interest': interest.pk, 'agreed_price': '45.50', 'pickup_details': 'Gate 2'}
    first = client.post(confirm_url(trip_request), body, headers={'Idempotency-Key': 'abc'})
    assert first.status_code == 201
    data = first.json()['data']
    assert data['status'] == 'CONFIRMED' and data['agreed_price'] == '45.50'
    assert data['counterpart']['phone'] == interest.driver.phone
    replay = client.post(confirm_url(trip_request), body, headers={'Idempotency-Key': 'abc'})
    assert replay.status_code == 200 and replay.json()['data']['id'] == data['id']
    assert client.post(confirm_url(trip_request), body).status_code == 409
    detail = client.get(reverse('request-detail', args=[trip_request.pk])).json()['data']
    assert detail['status'] == 'CONFIRMED' and detail['trip']['id'] == data['id']


def test_confirm_requires_price(auth_client, customer, trip_request, interest):
    response = auth_client(customer).post(confirm_url(trip_request), {'interest': interest.pk})
    assert response.status_code == 400 and 'agreed_price' in response.json()['errors']


def test_confirm_only_by_owner(auth_client, make_user, trip_request, interest):
    response = auth_client(make_user()).post(confirm_url(trip_request), {'interest': interest.pk, 'agreed_price': 1})
    assert response.status_code == 404
    assert not Trip.objects.exists()


def test_driver_interest_view_progressive_disclosure(auth_client, customer, trip_request, interest, make_interest):
    other = make_interest(trip_request)
    client = auth_client(interest.driver)
    row = client.get(reverse('driver-interests')).json()['data'][0]
    assert row['status'] == 'INTERESTED' and row['customer_phone'] is None and row['trip'] is None

    services.mark_contacted(trip_request, interest.pk, customer)
    row = client.get(reverse('driver-interests')).json()['data'][0]
    assert row['customer_phone'] == customer.phone

    confirm(trip_request, customer, interest)
    row = client.get(reverse('driver-interests')).json()['data'][0]
    assert row['status'] == 'SELECTED' and row['trip']['agreed_price'] == '50.00'
    assert row['trip']['counterpart']['phone'] == customer.phone

    loser = auth_client(other.driver).get(reverse('driver-interests')).json()['data'][0]
    assert loser['status'] == 'DECLINED' and loser['customer_phone'] is None and loser['trip'] is None
    assert loser['request']['status'] == 'CONFIRMED'


def test_driver_interests_exclude_withdrawn_and_require_driver_role(auth_client, customer, trip_request, make_interest):
    withdrawn = make_interest(trip_request, status='WITHDRAWN')
    assert auth_client(withdrawn.driver).get(reverse('driver-interests')).json()['data'] == []
    assert auth_client(customer).get(reverse('driver-interests')).status_code == 403

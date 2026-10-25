from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.notifications.models import Notification
from apps.trips import services
from apps.trips.models import StatusEvent, Trip
from common.exceptions import BusinessRuleError, ConflictError


@pytest.fixture
def trip(customer, trip_request, make_interest):
    return services.confirm_trip(trip_request, customer, interest_id=make_interest(trip_request).pk, agreed_price='30')[
        0
    ]


# --- service ---


def test_happy_path_logs_every_transition(trip, customer):
    services.start_trip(trip, trip.driver)
    services.complete_trip(trip, trip.driver)
    trip.refresh_from_db()
    assert trip.status == 'COMPLETED' and trip.started_at and trip.completed_at
    events = StatusEvent.objects.filter(object_type='Trip', object_id=trip.pk).values_list('to_status', flat=True)
    assert list(events) == ['CONFIRMED', 'IN_PROGRESS', 'COMPLETED']
    assert Notification.objects.filter(user=customer, type='TRIP_STARTED').count() == 1
    assert Notification.objects.filter(user=customer, type='TRIP_COMPLETED').count() == 1


def test_only_driver_starts(trip, customer):
    with pytest.raises(BusinessRuleError):
        services.start_trip(trip, customer)
    trip.refresh_from_db()
    assert trip.status == 'CONFIRMED'


def test_stranger_cannot_act(trip, make_user):
    stranger = make_user()
    for action in (services.start_trip, services.complete_trip, services.cancel_trip):
        with pytest.raises(BusinessRuleError):
            action(trip, stranger)


def test_cannot_complete_before_start(trip):
    with pytest.raises(ConflictError):
        services.complete_trip(trip, trip.driver)


def test_cannot_skip_or_repeat_start(trip):
    services.start_trip(trip, trip.driver)
    with pytest.raises(ConflictError):
        services.start_trip(trip, trip.driver)


@pytest.mark.parametrize('who', ['customer', 'driver'])
def test_either_party_cancels_before_start_and_other_is_told(trip, customer, who):
    actor = customer if who == 'customer' else trip.driver
    other = trip.driver if who == 'customer' else customer
    services.cancel_trip(trip, actor)
    trip.refresh_from_db()
    assert trip.status == 'CANCELLED' and trip.cancelled_at
    assert Notification.objects.filter(user=other, type='TRIP_CANCELLED').count() == 1
    assert not Notification.objects.filter(user=actor, type='TRIP_CANCELLED').exists()


def test_cancel_after_start_rejected(trip, customer):
    services.start_trip(trip, trip.driver)
    with pytest.raises(ConflictError):
        services.cancel_trip(trip, customer)
    trip.refresh_from_db()
    assert trip.status == 'IN_PROGRESS'


@pytest.mark.parametrize('first', ['complete', 'cancel'])
def test_terminal_trips_are_final(trip, customer, first):
    if first == 'complete':
        services.start_trip(trip, trip.driver)
        services.complete_trip(trip, customer)
    else:
        services.cancel_trip(trip, customer)
    for action in (services.start_trip, services.complete_trip, services.cancel_trip):
        with pytest.raises(ConflictError):
            action(trip, trip.driver)


def test_cancelled_trip_frees_the_driver(trip, customer):
    services.cancel_trip(trip, customer)
    from apps.matching.services import _has_capacity

    assert _has_capacity(trip.driver)


# --- API ---


def test_trip_list_and_detail_roles(auth_client, customer, trip):
    mine = auth_client(customer).get(reverse('trip-list')).json()['data']
    assert [t['id'] for t in mine] == [trip.pk] and mine[0]['role'] == 'customer'
    assert mine[0]['counterpart']['phone'] == trip.driver.phone
    detail = auth_client(trip.driver).get(reverse('trip-detail', args=[trip.pk])).json()['data']
    assert detail['role'] == 'driver' and detail['counterpart']['phone'] == customer.phone
    assert detail['pickup_area']['name'] == 'محطة'


def test_trip_hidden_from_others(auth_client, make_user, trip):
    other = auth_client(make_user())
    assert other.get(reverse('trip-detail', args=[trip.pk])).status_code == 404
    assert other.get(reverse('trip-list')).json()['data'] == []
    assert other.post(reverse('trip-start', args=[trip.pk])).status_code == 404


def test_endpoints_full_flow_and_illegal_jumps(auth_client, customer, trip):
    driver_client = auth_client(trip.driver)
    assert driver_client.post(reverse('trip-complete', args=[trip.pk])).status_code == 409
    assert driver_client.post(reverse('trip-start', args=[trip.pk])).json()['data']['status'] == 'IN_PROGRESS'
    assert driver_client.post(reverse('trip-start', args=[trip.pk])).status_code == 409
    assert driver_client.post(reverse('trip-cancel', args=[trip.pk])).status_code == 409
    assert driver_client.post(reverse('trip-complete', args=[trip.pk])).json()['data']['status'] == 'COMPLETED'
    assert Trip.objects.get(pk=trip.pk).status == 'COMPLETED'


def test_customer_cannot_start_via_api(auth_client, customer, trip):
    assert auth_client(customer).post(reverse('trip-start', args=[trip.pk])).status_code == 400


def test_cancelled_trip_shows_on_request_detail(auth_client, customer, trip):
    services.cancel_trip(trip, customer)
    data = auth_client(customer).get(reverse('request-detail', args=[trip.trip_request_id])).json()['data']
    assert data['status'] == 'CONFIRMED' and data['trip']['status'] == 'CANCELLED'


# --- reminders ---


def test_reminder_sent_once_for_requests_about_to_expire(make_request, settings):
    settings.REQUEST_REMINDER_MINUTES = 5
    soon = make_request(expires_at=timezone.now() + timedelta(minutes=3))
    make_request(expires_at=timezone.now() + timedelta(minutes=20))
    make_request(expires_at=timezone.now() + timedelta(minutes=3), status='CANCELLED')
    assert services.remind_expiring_requests() == 1
    assert services.remind_expiring_requests() == 0
    assert Notification.objects.filter(type='REQUEST_EXPIRING', related_object_id=soon.pk).count() == 1

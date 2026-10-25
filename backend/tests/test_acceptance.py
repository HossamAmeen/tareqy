"""End-to-end acceptance run of the 14 criteria in business doc section 20, through the public API only.

AC 8's truly parallel variant needs PostgreSQL row locks and lives in
apps/trips/tests/test_confirmation.py (skipped on SQLite); the sequential double-confirm is checked here.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import DriverProfile
from apps.trips.models import DriverInterest, StatusEvent, Trip, TripRequest


@pytest.fixture
def world(make_user, areas, auth_client):
    customer = make_user(name='Customer')
    drivers = []
    for i in range(2):
        user = make_user(name=f'Driver {i}', is_driver=True)
        DriverProfile.objects.create(user=user, is_verified=True)
        drivers.append(user)

    def go_live(driver):
        client = auth_client(driver)
        client.patch(reverse('driver-profile'), {'availability_status': 'AVAILABLE'})
        client.patch(reverse('driver-profile'), {'destination_area': areas['أربعين'].pk})
        client.post(
            reverse('driver-location'), {'latitude': '30.0', 'longitude': '32.0', 'current_area': areas['محطة'].pk}
        )

    return {'customer': customer, 'drivers': drivers, 'go_live': go_live, 'areas': areas, 'client': auth_client}


def create_request(w, **extra):
    payload = {'pickup_area': w['areas']['محطة'].pk, 'destination_area': w['areas']['أربعين'].pk, **extra}
    return w['client'](w['customer']).post(reverse('request-list'), payload)


def test_ac01_customer_creates_request_and_sees_status(world):
    response = create_request(world)
    assert response.status_code == 201 and response.json()['data']['status'] == 'OPEN'
    listed = world['client'](world['customer']).get(reverse('request-list')).json()['data']['results']
    assert [r['status'] for r in listed] == ['OPEN']


@pytest.mark.parametrize('missing', ['pickup_area', 'destination_area'])
def test_ac02_missing_pickup_or_destination_rejected(world, missing):
    payload = {'pickup_area': world['areas']['محطة'].pk, 'destination_area': world['areas']['أربعين'].pk}
    del payload[missing]
    assert world['client'](world['customer']).post(reverse('request-list'), payload).status_code == 400
    assert not TripRequest.objects.exists()


def test_ac03_driver_toggles_receiving(world):
    client = world['client'](world['drivers'][0])
    on = client.patch(reverse('driver-profile'), {'availability_status': 'AVAILABLE'}).json()['data']
    off = client.patch(reverse('driver-profile'), {'availability_status': 'OFFLINE'}).json()['data']
    assert (on['availability_status'], off['availability_status']) == ('AVAILABLE', 'OFFLINE')


def test_ac04_closed_requests_are_not_shown_as_new(world):
    world['go_live'](world['drivers'][0])
    open_id = create_request(world).json()['data']['id']
    closed_id = create_request(world).json()['data']['id']
    world['client'](world['customer']).post(reverse('request-cancel', args=[closed_id]))
    ids = [r['id'] for r in world['client'](world['drivers'][0]).get(reverse('driver-requests')).json()['data']]
    assert ids == [open_id]


def test_ac05_interest_without_duplicates(world):
    driver = world['drivers'][0]
    world['go_live'](driver)
    request_id = create_request(world).json()['data']['id']
    client = world['client'](driver)
    url = reverse('request-interest', args=[request_id])
    assert [client.post(url).status_code for _ in range(3)] == [201, 200, 200]
    assert DriverInterest.objects.filter(trip_request_id=request_id).count() == 1


def test_ac06_customer_can_contact_interested_driver(world):
    driver = world['drivers'][0]
    world['go_live'](driver)
    request_id = create_request(world).json()['data']['id']
    world['client'](driver).post(reverse('request-interest', args=[request_id]))
    rows = world['client'](world['customer']).get(reverse('request-interests', args=[request_id])).json()['data']
    assert rows[0]['driver']['phone'] == driver.phone


def test_ac07_interest_alone_does_not_confirm(world):
    driver = world['drivers'][0]
    world['go_live'](driver)
    request_id = create_request(world).json()['data']['id']
    world['client'](driver).post(reverse('request-interest', args=[request_id]))
    assert TripRequest.objects.get(pk=request_id).status == 'OPEN' and not Trip.objects.exists()


def test_ac08_only_one_driver_can_be_confirmed(world):
    for d in world['drivers']:
        world['go_live'](d)
    request_id = create_request(world).json()['data']['id']
    for d in world['drivers']:
        world['client'](d).post(reverse('request-interest', args=[request_id]))
    interests = DriverInterest.objects.filter(trip_request_id=request_id).order_by('id')
    client = world['client'](world['customer'])
    url = reverse('request-confirm', args=[request_id])
    first = client.post(url, {'interest': interests[0].pk, 'agreed_price': '20'})
    second = client.post(url, {'interest': interests[1].pk, 'agreed_price': '20'})
    assert (first.status_code, second.status_code) == (201, 409)
    assert Trip.objects.count() == 1


def test_ac09_unconfirmed_trip_cannot_start(world):
    """A trip that is not CONFIRMED (already cancelled) cannot be started."""
    driver = world['drivers'][0]
    world['go_live'](driver)
    request_id = create_request(world).json()['data']['id']
    world['client'](driver).post(reverse('request-interest', args=[request_id]))
    interest = DriverInterest.objects.get()
    trip_id = (
        world['client'](world['customer'])
        .post(reverse('request-confirm', args=[request_id]), {'interest': interest.pk, 'agreed_price': '9'})
        .json()['data']['id']
    )
    world['client'](world['customer']).post(reverse('trip-cancel', args=[trip_id]))
    assert world['client'](driver).post(reverse('trip-start', args=[trip_id])).status_code == 409
    assert Trip.objects.get().status == 'CANCELLED'


def test_ac10_trip_cannot_complete_before_start(world):
    driver = world['drivers'][0]
    world['go_live'](driver)
    request_id = create_request(world).json()['data']['id']
    world['client'](driver).post(reverse('request-interest', args=[request_id]))
    interest = DriverInterest.objects.get()
    trip_id = (
        world['client'](world['customer'])
        .post(reverse('request-confirm', args=[request_id]), {'interest': interest.pk, 'agreed_price': '9'})
        .json()['data']['id']
    )
    assert world['client'](driver).post(reverse('trip-complete', args=[trip_id])).status_code == 409
    assert world['client'](driver).post(reverse('trip-start', args=[trip_id])).status_code == 200
    assert world['client'](driver).post(reverse('trip-complete', args=[trip_id])).status_code == 200


def test_ac11_cancelling_stops_matching(world):
    driver = world['drivers'][0]
    world['go_live'](driver)
    request_id = create_request(world).json()['data']['id']
    # `client(user)` re-authenticates one shared test client, so always call it right before use.
    assert len(world['client'](driver).get(reverse('driver-requests')).json()['data']) == 1
    world['client'](world['customer']).post(reverse('request-cancel', args=[request_id]))
    assert world['client'](driver).get(reverse('driver-requests')).json()['data'] == []
    assert world['client'](driver).post(reverse('request-interest', args=[request_id])).status_code == 409


def test_ac12_expiry_blocks_confirmation(world):
    driver = world['drivers'][0]
    world['go_live'](driver)
    request_id = create_request(world).json()['data']['id']
    world['client'](driver).post(reverse('request-interest', args=[request_id]))
    TripRequest.objects.filter(pk=request_id).update(expires_at=timezone.now() - timedelta(seconds=1))
    interest = DriverInterest.objects.get()
    response = world['client'](world['customer']).post(
        reverse('request-confirm', args=[request_id]), {'interest': interest.pk, 'agreed_price': '9'}
    )
    assert response.status_code == 409 and not Trip.objects.exists()


def test_ac13_server_state_is_shown_without_any_notification(world):
    """State comes from the API itself: a confirmed trip is visible even if no push/notification was ever delivered."""
    driver = world['drivers'][0]
    world['go_live'](driver)
    request_id = create_request(world).json()['data']['id']
    world['client'](driver).post(reverse('request-interest', args=[request_id]))
    interest = DriverInterest.objects.get()
    world['client'](world['customer']).post(
        reverse('request-confirm', args=[request_id]), {'interest': interest.pk, 'agreed_price': '9'}
    )
    from apps.notifications.models import Notification

    Notification.objects.all().delete()
    row = world['client'](driver).get(reverse('driver-interests')).json()['data'][0]
    assert row['status'] == 'SELECTED' and row['trip']['status'] == 'CONFIRMED'
    detail = world['client'](world['customer']).get(reverse('request-detail', args=[request_id])).json()['data']
    assert detail['status'] == 'CONFIRMED' and detail['trip']['status'] == 'CONFIRMED'


def test_ac14_state_changes_are_logged_with_time(world):
    driver = world['drivers'][0]
    world['go_live'](driver)
    request_id = create_request(world).json()['data']['id']
    world['client'](driver).post(reverse('request-interest', args=[request_id]))
    interest = DriverInterest.objects.get()
    trip_id = (
        world['client'](world['customer'])
        .post(reverse('request-confirm', args=[request_id]), {'interest': interest.pk, 'agreed_price': '9'})
        .json()['data']['id']
    )
    world['client'](driver).post(reverse('trip-start', args=[trip_id]))
    world['client'](driver).post(reverse('trip-complete', args=[trip_id]))

    def history(kind, pk):
        return list(StatusEvent.objects.filter(object_type=kind, object_id=pk).values_list('to_status', flat=True))

    assert history('TripRequest', request_id) == ['OPEN', 'CONFIRMED']
    assert history('DriverInterest', interest.pk) == ['INTERESTED', 'SELECTED']
    assert history('Trip', trip_id) == ['CONFIRMED', 'IN_PROGRESS', 'COMPLETED']
    assert not StatusEvent.objects.filter(created_at__isnull=True).exists()

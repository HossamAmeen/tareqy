from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.trips.models import TripRequest


@pytest.fixture
def payload(areas):
    return {'pickup_area': areas['محطة'].pk, 'destination_area': areas['أربعين'].pk, 'notes': 'Gate 2'}


def test_requests_require_authentication(api_client):
    assert api_client.get(reverse('request-list')).status_code == 401


def test_driver_only_user_cannot_use_customer_api(auth_client, make_user):
    user = make_user(is_customer=False, is_driver=True)
    assert auth_client(user).get(reverse('request-list')).status_code == 403


def test_create_request(auth_client, customer, payload):
    response = auth_client(customer).post(reverse('request-list'), payload)
    assert response.status_code == 201
    data = response.json()['data']
    assert data['status'] == 'OPEN'
    assert data['pickup_area']['name'] == 'محطة'
    assert data['pickup_location_is_precise'] is False
    assert TripRequest.objects.filter(customer=customer).count() == 1


def test_create_request_with_precise_location(auth_client, customer, payload):
    payload.update(pickup_latitude='30.004', pickup_longitude='32.550')
    data = auth_client(customer).post(reverse('request-list'), payload).json()['data']
    assert data['pickup_location_is_precise'] is True


def test_create_requires_both_coordinates(auth_client, customer, payload):
    payload['pickup_latitude'] = '30.0'
    response = auth_client(customer).post(reverse('request-list'), payload)
    assert response.status_code == 400


@pytest.mark.parametrize('missing', ['pickup_area', 'destination_area'])
def test_create_rejects_missing_areas(auth_client, customer, payload, missing):
    del payload[missing]
    response = auth_client(customer).post(reverse('request-list'), payload)
    assert response.status_code == 400
    assert missing in response.json()['errors']
    assert not TripRequest.objects.exists()


def test_create_rejects_same_areas(auth_client, customer, payload):
    payload['destination_area'] = payload['pickup_area']
    response = auth_client(customer).post(reverse('request-list'), payload)
    assert response.status_code == 400
    assert response.json()['success'] is False


def test_create_rejects_unknown_area(auth_client, customer, payload):
    payload['pickup_area'] = 99999
    assert auth_client(customer).post(reverse('request-list'), payload).status_code == 400


def test_list_returns_only_own_requests_paginated(auth_client, customer, make_request, make_user):
    make_request()
    make_request(customer=make_user())
    data = auth_client(customer).get(reverse('request-list')).json()['data']
    assert data['count'] == 1 and len(data['results']) == 1


def test_cannot_read_someone_elses_request(auth_client, make_user, trip_request):
    other = make_user()
    assert auth_client(other).get(reverse('request-detail', args=[trip_request.pk])).status_code == 404


def test_retrieve_shows_expired_status(auth_client, customer, make_request):
    req = make_request(expires_at=timezone.now() - timedelta(seconds=1))
    data = auth_client(customer).get(reverse('request-detail', args=[req.pk])).json()['data']
    assert data['status'] == 'EXPIRED'


def test_patch_updates_notes(auth_client, customer, trip_request):
    response = auth_client(customer).patch(reverse('request-detail', args=[trip_request.pk]), {'notes': 'New'})
    assert response.status_code == 200
    trip_request.refresh_from_db()
    assert trip_request.notes == 'New'


def test_patch_cannot_edit_someone_elses_request(auth_client, make_user, trip_request):
    other = make_user()
    response = auth_client(other).patch(reverse('request-detail', args=[trip_request.pk]), {'notes': 'x'})
    assert response.status_code == 404


def test_patch_closed_request_returns_conflict(auth_client, customer, make_request):
    req = make_request(status='CANCELLED')
    response = auth_client(customer).patch(reverse('request-detail', args=[req.pk]), {'notes': 'x'})
    assert response.status_code == 409


def test_put_and_delete_are_not_allowed(auth_client, customer, trip_request):
    client = auth_client(customer)
    url = reverse('request-detail', args=[trip_request.pk])
    assert client.put(url, {}).status_code == 405
    assert client.delete(url).status_code == 405


def test_cancel_request(auth_client, customer, trip_request):
    response = auth_client(customer).post(reverse('request-cancel', args=[trip_request.pk]))
    assert response.status_code == 200
    assert response.json()['data']['status'] == 'CANCELLED'


def test_cancel_twice_returns_conflict(auth_client, customer, trip_request):
    client = auth_client(customer)
    url = reverse('request-cancel', args=[trip_request.pk])
    assert client.post(url).status_code == 200
    assert client.post(url).status_code == 409


def test_cancelled_request_is_not_listed_as_open(auth_client, customer, make_request):
    make_request(status='CANCELLED')
    results = auth_client(customer).get(reverse('request-list')).json()['data']['results']
    assert [r['status'] for r in results] == ['CANCELLED']

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import DriverProfile
from apps.notifications.models import Notification
from apps.trips.models import DriverInterest, StatusEvent, TripRequest


def interest_url(req):
    return reverse('request-interest', args=[req.pk])


# --- driver profile / location ---


def test_driver_endpoints_require_driver_role(auth_client, customer):
    client = auth_client(customer)
    assert client.get(reverse('driver-profile')).status_code == 403
    assert client.get(reverse('driver-requests')).status_code == 403
    assert client.post(reverse('driver-location'), {'latitude': 1, 'longitude': 1}).status_code == 403


def test_profile_created_on_first_read(auth_client, driver):
    data = auth_client(driver).get(reverse('driver-profile')).json()['data']
    assert data['availability_status'] == 'OFFLINE'
    assert data['location_status'] == 'none'
    assert data['destination_area'] is None


def test_toggle_availability(auth_client, driver):
    response = auth_client(driver).patch(reverse('driver-profile'), {'availability_status': 'AVAILABLE'})
    assert response.json()['data']['availability_status'] == 'AVAILABLE'
    assert DriverProfile.objects.get(user=driver).availability_status == 'AVAILABLE'


def test_set_destination_with_expiry(auth_client, driver, areas, settings):
    settings.DRIVER_DESTINATION_TTL_MINUTES = 60
    response = auth_client(driver).patch(reverse('driver-profile'), {'destination_area': areas['أربعين'].pk})
    profile = DriverProfile.objects.get(user=driver)
    assert response.json()['data']['destination_area']['name'] == 'أربعين'
    assert timezone.now() + timedelta(minutes=59) < profile.destination_expires_at


def test_custom_destination_ttl_and_clear(auth_client, driver, areas):
    client = auth_client(driver)
    client.patch(reverse('driver-profile'), {'destination_area': areas['أربعين'].pk, 'destination_ttl_minutes': 15})
    expires = DriverProfile.objects.get(user=driver).destination_expires_at
    assert expires < timezone.now() + timedelta(minutes=16)
    client.patch(reverse('driver-profile'), {'destination_area': None}, format='json')
    profile = DriverProfile.objects.get(user=driver)
    assert profile.destination_area is None and profile.destination_expires_at is None


def test_expired_destination_is_not_reported(auth_client, driver, areas):
    DriverProfile.objects.create(
        user=driver, destination_area=areas['أربعين'], destination_expires_at=timezone.now() - timedelta(minutes=1)
    )
    assert auth_client(driver).get(reverse('driver-profile')).json()['data']['destination_area'] is None


def test_ttl_without_destination_rejected(auth_client, driver):
    response = auth_client(driver).patch(reverse('driver-profile'), {'destination_ttl_minutes': 30})
    assert response.status_code == 400


def test_inactive_destination_rejected(auth_client, driver, areas):
    areas['أربعين'].is_active = False
    areas['أربعين'].save()
    response = auth_client(driver).patch(reverse('driver-profile'), {'destination_area': areas['أربعين'].pk})
    assert response.status_code == 400


def test_location_update_sets_freshness_and_nearest_area(auth_client, driver, areas):
    areas['محطة'].latitude, areas['محطة'].longitude = Decimal('30.000000'), Decimal('32.000000')
    areas['محطة'].save()
    response = auth_client(driver).post(reverse('driver-location'), {'latitude': '30.001', 'longitude': '32.001'})
    data = response.json()['data']
    assert data['location_status'] == 'fresh'
    assert data['current_area']['name'] == 'محطة'


def test_location_explicit_area(auth_client, driver, areas):
    payload = {'latitude': '30.0', 'longitude': '32.0', 'current_area': areas['معلمين'].pk}
    data = auth_client(driver).post(reverse('driver-location'), payload).json()['data']
    assert data['current_area']['name'] == 'معلمين'


def test_location_outside_any_area_clears_area(auth_client, driver):
    data = auth_client(driver).post(reverse('driver-location'), {'latitude': '10', 'longitude': '10'}).json()['data']
    assert data['current_area'] is None


@pytest.mark.parametrize('payload', [{'latitude': '91', 'longitude': '0'}, {'latitude': '0'}])
def test_location_validation(auth_client, driver, payload):
    assert auth_client(driver).post(reverse('driver-location'), payload).status_code == 400


def test_stale_location_reported(auth_client, driver):
    DriverProfile.objects.create(user=driver, location_updated_at=timezone.now() - timedelta(hours=1))
    assert auth_client(driver).get(reverse('driver-profile')).json()['data']['location_status'] == 'stale'


# --- matching list ---


def test_request_list_is_estimated_and_hides_customer(auth_client, make_driver, trip_request):
    profile = make_driver()
    rows = auth_client(profile.user).get(reverse('driver-requests')).json()['data']
    assert [r['id'] for r in rows] == [trip_request.pk]
    assert rows[0]['match_type'] == 'estimated'
    assert rows[0]['my_interest'] is None
    assert 'customer' not in rows[0] and 'phone' not in str(rows[0])


def test_request_list_empty_for_offline_driver(auth_client, driver, trip_request):
    assert auth_client(driver).get(reverse('driver-requests')).json()['data'] == []


def test_closed_requests_not_listed(auth_client, make_driver, trip_request):
    profile = make_driver()
    trip_request.status = TripRequest.Status.CANCELLED
    trip_request.save()
    assert auth_client(profile.user).get(reverse('driver-requests')).json()['data'] == []


# --- interest ---


def test_express_interest(auth_client, make_driver, trip_request):
    profile = make_driver()
    response = auth_client(profile.user).post(interest_url(trip_request))
    assert response.status_code == 201
    interest = DriverInterest.objects.get(trip_request=trip_request, driver=profile.user)
    assert interest.status == 'INTERESTED'
    assert StatusEvent.objects.filter(object_type='DriverInterest', object_id=interest.pk).count() == 1
    assert Notification.objects.filter(user=trip_request.customer, type='DRIVER_INTERESTED').count() == 1
    rows = auth_client(profile.user).get(reverse('driver-requests')).json()['data']
    assert rows[0]['my_interest'] == 'INTERESTED'


def test_interest_is_idempotent_no_duplicates(auth_client, make_driver, trip_request):
    profile = make_driver()
    client = auth_client(profile.user)
    assert client.post(interest_url(trip_request)).status_code == 201
    assert client.post(interest_url(trip_request)).status_code == 200
    assert DriverInterest.objects.filter(trip_request=trip_request).count() == 1
    assert Notification.objects.filter(type='DRIVER_INTERESTED').count() == 1


def test_multiple_drivers_can_be_interested(auth_client, make_driver, trip_request):
    for _ in range(2):
        assert auth_client(make_driver().user).post(interest_url(trip_request)).status_code == 201
    assert DriverInterest.objects.filter(trip_request=trip_request).count() == 2


@pytest.mark.parametrize('status', ['CONFIRMED', 'CANCELLED', 'EXPIRED'])
def test_interest_blocked_on_closed_request(auth_client, make_driver, make_request, status):
    request = make_request(status=status)
    response = auth_client(make_driver().user).post(interest_url(request))
    assert response.status_code == 409
    assert not DriverInterest.objects.exists()


def test_interest_blocked_on_time_expired_request(auth_client, make_driver, make_request):
    request = make_request(expires_at=timezone.now() - timedelta(seconds=1))
    assert auth_client(make_driver().user).post(interest_url(request)).status_code == 409


def test_interest_blocked_for_non_matching_driver(auth_client, make_driver, trip_request, areas):
    profile = make_driver(destination_area=areas['معلمين'])
    assert auth_client(profile.user).post(interest_url(trip_request)).status_code == 400


def test_interest_blocked_for_offline_driver(auth_client, make_driver, trip_request):
    profile = make_driver(availability_status='OFFLINE')
    assert auth_client(profile.user).post(interest_url(trip_request)).status_code == 400


def test_interest_unknown_request(auth_client, make_driver):
    assert auth_client(make_driver().user).post(reverse('request-interest', args=[999])).status_code == 400


def test_customer_cannot_express_interest(auth_client, customer, trip_request):
    assert auth_client(customer).post(interest_url(trip_request)).status_code == 403


def test_withdraw_and_reinterest(auth_client, make_driver, trip_request):
    profile = make_driver()
    client = auth_client(profile.user)
    client.post(interest_url(trip_request))
    response = client.delete(interest_url(trip_request))
    assert response.status_code == 200
    assert response.json()['data']['status'] == 'WITHDRAWN'
    assert client.delete(interest_url(trip_request)).status_code == 200  # idempotent
    assert client.post(interest_url(trip_request)).status_code == 201  # reopened, same row
    interest = DriverInterest.objects.get(trip_request=trip_request)
    assert interest.status == 'INTERESTED'
    assert DriverInterest.objects.count() == 1


def test_withdraw_without_interest(auth_client, make_driver, trip_request):
    assert auth_client(make_driver().user).delete(interest_url(trip_request)).status_code == 400


def test_selected_driver_cannot_withdraw(auth_client, make_driver, make_interest, trip_request):
    profile = make_driver()
    DriverInterest.objects.create(trip_request=trip_request, driver=profile.user, status='SELECTED')
    assert auth_client(profile.user).delete(interest_url(trip_request)).status_code == 409


def test_reinterest_after_request_edit_declined_it(auth_client, make_driver, trip_request):
    profile = make_driver()
    DriverInterest.objects.create(trip_request=trip_request, driver=profile.user, status='DECLINED')
    assert auth_client(profile.user).post(interest_url(trip_request)).status_code == 201

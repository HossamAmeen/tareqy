import pytest
from django.urls import reverse

from apps.accounts.models import DriverProfile
from apps.reports.models import Report
from apps.trips import services
from apps.trips.models import StatusEvent

LIST_ROUTES = ['admin-user-list', 'admin-request-list', 'admin-trip-list', 'admin-report-list', 'admin-kpis']


@pytest.mark.parametrize('route', LIST_ROUTES)
def test_admin_api_requires_staff(auth_client, api_client, customer, driver, route):
    assert api_client.get(reverse(route)).status_code == 401
    assert auth_client(customer).get(reverse(route)).status_code == 403
    assert auth_client(driver).get(reverse(route)).status_code == 403


@pytest.mark.parametrize('route', LIST_ROUTES)
def test_staff_can_read(auth_client, staff, route):
    assert auth_client(staff).get(reverse(route)).status_code == 200


def test_user_list_filters(auth_client, staff, customer, driver):
    client = auth_client(staff)
    rows = client.get(reverse('admin-user-list'), {'role': 'driver'}).json()['data']['results']
    assert [r['id'] for r in rows] == [driver.pk]
    rows = client.get(reverse('admin-user-list'), {'search': customer.phone}).json()['data']['results']
    assert [r['id'] for r in rows] == [customer.pk]


def test_suspend_blocks_login_and_is_audited(auth_client, staff, customer):
    client = auth_client(staff)
    response = client.post(reverse('admin-user-suspend', args=[customer.pk]))
    assert response.json()['data']['account_status'] == 'SUSPENDED'
    event = StatusEvent.objects.get(object_type='User', object_id=customer.pk)
    assert (event.from_status, event.to_status, event.actor) == ('ACTIVE', 'SUSPENDED', staff)

    from rest_framework.test import APIClient

    token = APIClient()
    token.force_authenticate(customer)
    # A suspended account is no longer active, so real token auth rejects it.
    customer.refresh_from_db()
    assert not customer.is_active
    client.post(reverse('admin-user-activate', args=[customer.pk]))
    customer.refresh_from_db()
    assert customer.is_active


def test_staff_cannot_suspend_self_or_other_staff(auth_client, staff, make_user):
    client = auth_client(staff)
    assert client.post(reverse('admin-user-suspend', args=[staff.pk])).status_code == 400
    other = make_user(is_staff=True)
    assert client.post(reverse('admin-user-suspend', args=[other.pk])).status_code == 400


def test_suspended_user_cannot_use_real_token(api_client, customer, staff, auth_client):
    from rest_framework_simplejwt.tokens import RefreshToken

    access = str(RefreshToken.for_user(customer).access_token)
    assert api_client.get(reverse('me'), HTTP_AUTHORIZATION=f'Bearer {access}').status_code == 200
    auth_client(staff).post(reverse('admin-user-suspend', args=[customer.pk]))
    api_client.force_authenticate(None)
    assert api_client.get(reverse('me'), HTTP_AUTHORIZATION=f'Bearer {access}').status_code == 401


def test_verify_and_unverify_driver(auth_client, staff, driver):
    client = auth_client(staff)
    assert client.post(reverse('admin-user-verify-driver', args=[driver.pk])).json()['data']['is_verified'] is True
    profile = DriverProfile.objects.get(user=driver)
    assert profile.is_verified and profile.verified_at
    profile.availability_status = 'AVAILABLE'
    profile.save()
    assert client.post(reverse('admin-user-unverify-driver', args=[driver.pk])).json()['data']['is_verified'] is False
    profile.refresh_from_db()
    assert profile.availability_status == 'OFFLINE'


def test_cannot_verify_non_driver(auth_client, staff, customer):
    assert auth_client(staff).post(reverse('admin-user-verify-driver', args=[customer.pk])).status_code == 400


def test_request_and_trip_detail_include_status_history(auth_client, staff, customer, trip_request, make_interest):
    services.confirm_trip(trip_request, customer, interest_id=make_interest(trip_request).pk, agreed_price='5')
    client = auth_client(staff)
    request_data = client.get(reverse('admin-request-detail', args=[trip_request.pk])).json()['data']
    assert request_data['customer'] == customer.phone and request_data['interest_count'] == 1
    assert [e['to_status'] for e in request_data['history']] == ['CONFIRMED']
    trip_id = client.get(reverse('admin-trip-list')).json()['data']['results'][0]['id']
    trip_data = client.get(reverse('admin-trip-detail', args=[trip_id])).json()['data']
    assert [e['to_status'] for e in trip_data['history']] == ['CONFIRMED']


def test_request_list_status_filter(auth_client, staff, make_request):
    make_request()
    make_request(status='CANCELLED')
    rows = auth_client(staff).get(reverse('admin-request-list'), {'status': 'CANCELLED'}).json()['data']['results']
    assert [r['status'] for r in rows] == ['CANCELLED']


def test_review_report_flow(auth_client, staff, customer, driver):
    report = Report.objects.create(reporter=customer, related_user=driver, reason='rude')
    client = auth_client(staff)
    url = reverse('admin-report-review', args=[report.pk])
    assert client.post(url, {'status': 'REVIEWING'}).json()['data']['status'] == 'REVIEWING'
    done = client.post(url, {'status': 'RESOLVED', 'note': 'warned driver'}).json()['data']
    assert done['status'] == 'RESOLVED' and done['resolution_note'] == 'warned driver' and done['resolved_at']
    assert client.post(url, {'status': 'DISMISSED'}).status_code == 409
    assert client.post(url, {'status': 'OPEN'}).status_code == 400
    assert list(StatusEvent.objects.filter(object_type='Report').values_list('to_status', flat=True)) == [
        'REVIEWING',
        'RESOLVED',
    ]


def test_non_staff_cannot_review(auth_client, customer, driver):
    report = Report.objects.create(reporter=customer, related_user=driver, reason='x')
    assert (
        auth_client(customer).post(reverse('admin-report-review', args=[report.pk]), {'status': 'RESOLVED'}).status_code
        == 403
    )

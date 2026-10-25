import pytest
from django.urls import reverse

from apps.reports.models import Report
from apps.trips import services


@pytest.fixture
def trip(customer, trip_request, make_interest):
    return services.confirm_trip(trip_request, customer, interest_id=make_interest(trip_request).pk, agreed_price='5')[
        0
    ]


def post(client, **payload):
    return client.post(reverse('report-create'), payload, format='json')


def test_report_requires_auth(api_client):
    assert post(api_client, reason='something bad').status_code == 401


def test_customer_reports_trip_and_driver_is_derived(auth_client, customer, trip):
    response = post(auth_client(customer), trip=trip.pk, reason='driver was rude')
    assert response.status_code == 201
    report = Report.objects.get()
    assert (report.reporter, report.related_user, report.trip, report.status) == (customer, trip.driver, trip, 'OPEN')


def test_driver_reports_trip_and_customer_is_derived(auth_client, customer, trip):
    post(auth_client(trip.driver), trip=trip.pk, reason='no show at pickup')
    assert Report.objects.get().related_user == customer


def test_cannot_report_someone_elses_trip(auth_client, make_user, trip):
    assert post(auth_client(make_user()), trip=trip.pk, reason='not my trip').status_code == 400
    assert not Report.objects.exists()


def test_report_user_requires_shared_trip(auth_client, customer, driver, trip, make_user):
    assert post(auth_client(customer), related_user=trip.driver_id, reason='bad driving').status_code == 201
    assert post(auth_client(customer), related_user=driver.pk, reason='unrelated person').status_code == 400
    assert post(auth_client(customer), related_user=customer.pk, reason='myself').status_code == 400


def test_report_needs_a_target_and_a_reason(auth_client, customer, trip):
    client = auth_client(customer)
    assert post(client, reason='no target at all').status_code == 400
    assert post(client, trip=trip.pk, reason='no').status_code == 400
    assert post(client, trip=trip.pk, reason='x' * 1001).status_code == 400
    assert post(client, trip=99999, reason='unknown trip').status_code == 400


def test_response_does_not_leak_other_party(auth_client, customer, trip):
    data = post(auth_client(customer), trip=trip.pk, reason='driver was rude').json()['data']
    assert set(data) == {'id', 'trip', 'status', 'created_at'}

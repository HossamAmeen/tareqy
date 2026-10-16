import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_validation_error_uses_standard_format(api_client):
    response = api_client.post(reverse('token'), {})
    assert response.status_code == 400
    body = response.json()
    assert body['success'] is False
    assert body['message'] == 'Validation failed.'
    assert 'phone' in body['errors']


@pytest.mark.django_db
def test_authentication_error_uses_standard_format(api_client):
    response = api_client.post(reverse('token'), {'phone': '+201000000000', 'password': 'y'})
    assert response.status_code == 401
    assert response.json()['success'] is False

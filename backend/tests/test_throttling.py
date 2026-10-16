import pytest
from django.urls import reverse
from rest_framework.throttling import SimpleRateThrottle


def _set_rates(monkeypatch, **rates):
    current = dict(SimpleRateThrottle.THROTTLE_RATES)
    current.update(rates)
    monkeypatch.setattr(SimpleRateThrottle, 'THROTTLE_RATES', current)


def test_api_allows_requests_within_rate_limit(api_client, monkeypatch):
    _set_rates(monkeypatch, health='3/minute')
    url = reverse('health')
    for _ in range(3):
        assert api_client.get(url, {'password': 'test-health-secret'}).status_code == 200


def test_api_rejects_requests_after_rate_limit_with_standard_error(api_client, monkeypatch):
    _set_rates(monkeypatch, health='2/minute')
    url = reverse('health')
    for _ in range(2):
        api_client.get(url, {'password': 'test-health-secret'})
    response = api_client.get(url, {'password': 'test-health-secret'})
    assert response.status_code == 429
    assert response.json() == {
        'success': False,
        'message': 'Request rate limit exceeded.',
        'errors': {},
    }
    assert 'Retry-After' in response


@pytest.mark.django_db
def test_auth_endpoint_uses_stricter_throttle(api_client, monkeypatch):
    _set_rates(monkeypatch, auth='2/minute', anon='1000/minute')
    url = reverse('token')
    payload = {'phone': '+201000000000', 'password': 'x'}
    assert api_client.post(url, payload).status_code == 401
    assert api_client.post(url, payload).status_code == 401
    assert api_client.post(url, payload).status_code == 429


@pytest.mark.django_db
def test_anonymous_user_uses_anonymous_throttle(api_client, monkeypatch):
    _set_rates(monkeypatch, anon='1/minute')
    url = reverse('swagger-ui')
    # health has its own scope; the schema endpoint uses the global anon throttle
    assert api_client.get(reverse('schema')).status_code == 200
    assert api_client.get(reverse('schema')).status_code == 429
    assert url


@pytest.mark.django_db
def test_authenticated_user_uses_user_throttle(api_client, monkeypatch, django_user_model):
    _set_rates(monkeypatch, user='1/minute', anon='1000/minute')
    user = django_user_model.objects.create_user(phone='+201000000111', password='pw12345678')
    api_client.force_authenticate(user)
    assert api_client.get(reverse('schema')).status_code == 200
    assert api_client.get(reverse('schema')).status_code == 429

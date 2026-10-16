import pytest
from django.urls import reverse


@pytest.fixture
def url():
    return reverse('health')


def test_health_endpoint_returns_success_with_valid_password(api_client, url):
    response = api_client.get(url, {'password': 'test-health-secret'})
    assert response.status_code == 200
    assert response.json() == {
        'success': True,
        'message': 'Service is healthy.',
        'data': {'status': 'healthy'},
    }


def test_health_endpoint_accepts_header_token(api_client, url):
    response = api_client.get(url, HTTP_X_HEALTH_CHECK_TOKEN='test-health-secret')
    assert response.status_code == 200


def test_health_endpoint_rejects_invalid_password(api_client, url):
    response = api_client.get(url, {'password': 'wrong'})
    assert response.status_code == 403
    assert response.json() == {
        'success': False,
        'message': 'Invalid health check password.',
        'errors': {},
    }


def test_health_endpoint_requires_password(api_client, url):
    assert api_client.get(url).status_code == 403


def test_health_endpoint_rejects_when_password_not_configured(api_client, url, settings):
    settings.HEALTH_CHECK_PASSWORD = ''
    assert api_client.get(url, {'password': ''}).status_code == 403


def test_health_endpoint_does_not_expose_secret(api_client, url):
    response = api_client.get(url, {'password': 'test-health-secret'})
    assert 'test-health-secret' not in response.content.decode()


@pytest.mark.django_db
def test_readiness_ok_without_celery(api_client, settings):
    settings.CELERY_ENABLED = False
    response = api_client.get(reverse('health-ready'), {'password': 'test-health-secret'})
    assert response.status_code == 200
    assert response.json()['data'] == {'database': 'ok'}


def test_readiness_requires_password(api_client):
    assert api_client.get(reverse('health-ready')).status_code == 403

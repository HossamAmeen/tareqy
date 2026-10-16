from django.urls import reverse

from apps.accounts.models import DriverProfile


def test_me_requires_authentication(api_client):
    assert api_client.get(reverse('me')).status_code == 401


def test_me_returns_profile(auth_client, customer):
    data = auth_client(customer).get(reverse('me')).json()['data']
    assert data['phone'] == customer.phone and data['is_customer'] is True


def test_patch_me_updates_name(auth_client, customer):
    response = auth_client(customer).patch(reverse('me'), {'name': 'Ali'})
    assert response.status_code == 200
    customer.refresh_from_db()
    assert customer.name == 'Ali'


def test_enabling_driver_role_creates_driver_profile(auth_client, customer):
    response = auth_client(customer).patch(reverse('me'), {'is_driver': True})
    assert response.status_code == 200
    assert DriverProfile.objects.filter(user=customer).exists()


def test_cannot_disable_all_roles(auth_client, customer):
    response = auth_client(customer).patch(reverse('me'), {'is_customer': False})
    assert response.status_code == 400
    customer.refresh_from_db()
    assert customer.is_customer is True


def test_me_cannot_change_phone_or_status(auth_client, customer):
    old = customer.phone
    auth_client(customer).patch(reverse('me'), {'phone': '+201055555555', 'account_status': 'SUSPENDED'})
    customer.refresh_from_db()
    assert customer.phone == old and customer.account_status == 'ACTIVE'

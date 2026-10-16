from rest_framework.test import APIRequestFactory

from apps.accounts.permissions import IsAdmin, IsCustomer, IsDriver

factory = APIRequestFactory()


def _request(user):
    request = factory.get('/')
    request.user = user
    return request


def test_role_permissions(customer, driver, staff):
    assert IsCustomer().has_permission(_request(customer), None)
    assert not IsDriver().has_permission(_request(customer), None)
    assert IsDriver().has_permission(_request(driver), None)
    assert IsAdmin().has_permission(_request(staff), None)
    assert not IsAdmin().has_permission(_request(customer), None)


def test_permissions_deny_anonymous():
    from django.contrib.auth.models import AnonymousUser

    request = _request(AnonymousUser())
    assert not IsCustomer().has_permission(request, None)
    assert not IsDriver().has_permission(request, None)
    assert not IsAdmin().has_permission(request, None)

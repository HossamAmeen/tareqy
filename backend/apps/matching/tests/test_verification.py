from django.urls import reverse

from apps.matching import services


def test_unverified_driver_cannot_go_available(settings, auth_client, driver):
    settings.DRIVER_VERIFICATION_REQUIRED = True
    response = auth_client(driver).patch(reverse('driver-profile'), {'availability_status': 'AVAILABLE'})
    assert response.status_code == 400
    assert 'verification' in response.json()['message']
    assert auth_client(driver).get(reverse('driver-profile')).json()['data']['is_verified'] is False


def test_verified_driver_can_go_available(settings, auth_client, driver):
    settings.DRIVER_VERIFICATION_REQUIRED = True
    from apps.accounts.models import DriverProfile

    DriverProfile.objects.create(user=driver, is_verified=True)
    response = auth_client(driver).patch(reverse('driver-profile'), {'availability_status': 'AVAILABLE'})
    assert response.status_code == 200


def test_unverified_driver_gets_no_matches_even_if_flagged_available(settings, make_driver, trip_request):
    settings.DRIVER_VERIFICATION_REQUIRED = True
    profile = make_driver(is_verified=False)
    assert services.matching_requests(profile.user) == []
    profile.is_verified = True
    profile.save()
    assert len(services.matching_requests(profile.user)) == 1


def test_offline_toggle_never_needs_verification(settings, auth_client, driver):
    settings.DRIVER_VERIFICATION_REQUIRED = True
    assert auth_client(driver).patch(reverse('driver-profile'), {'availability_status': 'OFFLINE'}).status_code == 200

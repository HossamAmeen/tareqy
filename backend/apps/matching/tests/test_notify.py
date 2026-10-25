from apps.matching import services
from apps.notifications.models import Notification


def test_matching_available_drivers_are_alerted_once(make_driver, trip_request, areas, compat):
    match = make_driver()
    make_driver(availability_status='OFFLINE')
    make_driver(destination_area=areas['معلمين'])
    assert services.notify_matching_drivers(trip_request.pk) == 1
    assert services.notify_matching_drivers(trip_request.pk) == 1
    assert Notification.objects.filter(type='NEW_MATCHING_REQUEST').count() == 1
    assert Notification.objects.get().user == match.user


def test_no_alert_for_closed_request(make_driver, trip_request):
    make_driver()
    trip_request.status = 'CANCELLED'
    trip_request.save()
    assert services.notify_matching_drivers(trip_request.pk) == 0


def test_unknown_request_is_ignored(db):
    assert services.notify_matching_drivers(12345) == 0

from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.notifications import push, services
from apps.notifications.models import Notification, PushSubscription

SUB = {'endpoint': 'https://push.example/abc', 'p256dh': 'key', 'auth': 'secret'}


@pytest.fixture
def push_on(settings):
    settings.VAPID_PUBLIC_KEY, settings.VAPID_PRIVATE_KEY = 'pub', 'priv'


def make_sub(user, endpoint=SUB['endpoint']):
    return PushSubscription.objects.create(user=user, endpoint=endpoint, p256dh='k', auth='a')


# --- in-app centre ---


def test_list_returns_only_own_with_unread_count(auth_client, customer, driver):
    mine = services.create_notification(customer, 'DRIVER_INTERESTED', 1)
    services.create_notification(driver, 'TRIP_CONFIRMED', 2)
    data = auth_client(customer).get(reverse('notification-list')).json()['data']
    assert data['unread_count'] == 1
    assert [n['id'] for n in data['results']] == [mine.pk]
    assert data['results'][0]['title'] and 'phone' not in str(data['results'][0])


def test_mark_read_and_idempotent(auth_client, customer):
    n = services.create_notification(customer, 'TRIP_CONFIRMED', 1)
    client = auth_client(customer)
    assert client.post(reverse('notification-read', args=[n.pk])).status_code == 200
    first = Notification.objects.get(pk=n.pk).read_at
    client.post(reverse('notification-read', args=[n.pk]))
    assert Notification.objects.get(pk=n.pk).read_at == first
    assert client.get(reverse('notification-list')).json()['data']['unread_count'] == 0


def test_cannot_read_someone_elses_notification(auth_client, customer, driver):
    n = services.create_notification(driver, 'TRIP_CONFIRMED', 1)
    assert auth_client(customer).post(reverse('notification-read', args=[n.pk])).status_code == 400
    assert Notification.objects.get(pk=n.pk).read_at is None


def test_duplicate_event_creates_one_notification(customer):
    for _ in range(3):
        services.create_notification(customer, 'TRIP_CONFIRMED', 1, dedupe_key='same')
    assert Notification.objects.count() == 1


def test_notifications_require_auth(api_client):
    assert api_client.get(reverse('notification-list')).status_code == 401


# --- subscriptions ---


def test_public_key_reports_disabled_without_keys(auth_client, customer):
    data = auth_client(customer).get(reverse('push-public-key')).json()['data']
    assert data == {'enabled': False, 'public_key': ''}


def test_subscribe_is_idempotent_and_unsubscribe(auth_client, customer):
    client = auth_client(customer)
    assert client.post(reverse('push-subscription'), SUB).status_code == 200
    client.post(reverse('push-subscription'), SUB)
    assert PushSubscription.objects.filter(user=customer).count() == 1
    client.delete(reverse('push-subscription'), {'endpoint': SUB['endpoint']}, format='json')
    assert not PushSubscription.objects.exists()


def test_subscribe_validates(auth_client, customer):
    assert auth_client(customer).post(reverse('push-subscription'), {'endpoint': 'nope'}).status_code == 400


def test_unsubscribe_cannot_remove_another_users_device(auth_client, customer, driver):
    make_sub(driver)
    auth_client(customer).delete(reverse('push-subscription'), {'endpoint': SUB['endpoint']}, format='json')
    assert PushSubscription.objects.count() == 1


# --- delivery ---


def deliver(n):
    services.deliver_push(n.pk)
    n.refresh_from_db()
    return n.delivery_status


def test_delivery_sends_payload_without_personal_data(push_on, customer):
    make_sub(customer)
    n = services.create_notification(customer, 'DRIVER_INTERESTED', 7)
    with patch.object(push, 'send_web_push') as send:
        assert deliver(n) == 'SENT'
    payload = send.call_args.args[1]
    assert payload['type'] == 'DRIVER_INTERESTED' and payload['related_object_id'] == 7
    assert customer.phone not in str(payload)


def test_delivery_skipped_without_subscription_or_keys(push_on, customer, settings):
    n = services.create_notification(customer, 'X')
    assert deliver(n) == 'SKIPPED'
    make_sub(customer)
    settings.VAPID_PRIVATE_KEY = ''
    n2 = services.create_notification(customer, 'X')
    assert deliver(n2) == 'SKIPPED'


def test_delivery_runs_once(push_on, customer):
    make_sub(customer)
    n = services.create_notification(customer, 'X')
    with patch.object(push, 'send_web_push') as send:
        deliver(n)
        deliver(n)
    assert send.call_count == 1


def test_gone_subscription_is_removed(push_on, customer):
    make_sub(customer)
    n = services.create_notification(customer, 'X')
    with patch.object(push, 'send_web_push', side_effect=push.SubscriptionGone):
        assert deliver(n) == 'SKIPPED'
    assert not PushSubscription.objects.exists()


def test_failure_raises_for_retry_and_leaves_row_pending(push_on, customer):
    make_sub(customer)
    n = services.create_notification(customer, 'X')
    with patch.object(push, 'send_web_push', side_effect=RuntimeError('network')):
        with pytest.raises(services.PushDeliveryError):
            services.deliver_push(n.pk)
    n.refresh_from_db()
    assert n.delivery_status == 'PENDING'


def test_task_marks_failed_after_retries_and_never_raises(push_on, customer):
    from apps.notifications.tasks import send_push

    make_sub(customer)
    n = services.create_notification(customer, 'X')
    with patch.object(push, 'send_web_push', side_effect=RuntimeError('network')):
        send_push.apply(args=[n.pk]).get()
    n.refresh_from_db()
    assert n.delivery_status == 'FAILED'


def test_push_failure_does_not_affect_business_state(push_on, customer, make_interest, trip_request):
    """A failing push backend must not break confirming a trip (AC 13/14)."""
    from apps.trips import services as trip_services

    make_sub(trip_request.customer)
    interest = make_interest(trip_request)
    with patch.object(push, 'send_web_push', side_effect=RuntimeError('boom')):
        trip, _ = trip_services.confirm_trip(trip_request, customer, interest_id=interest.pk, agreed_price='5')
    trip_request.refresh_from_db()
    assert trip.pk and trip_request.status == 'CONFIRMED'

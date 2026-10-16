from apps.notifications.models import Notification
from apps.notifications.services import create_notification


def test_dedupe_key_prevents_duplicates(customer):
    first = create_notification(customer, 'X', 1, dedupe_key='k1')
    second = create_notification(customer, 'X', 1, dedupe_key='k1')
    assert first.pk == second.pk
    assert Notification.objects.count() == 1


def test_without_dedupe_key_creates_each_time(customer):
    create_notification(customer, 'X')
    create_notification(customer, 'X')
    assert Notification.objects.count() == 2

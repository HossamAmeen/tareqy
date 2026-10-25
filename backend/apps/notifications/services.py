import logging

from django.db import transaction
from django.utils import timezone

from . import push
from .messages import message_for
from .models import Notification, PushSubscription

logger = logging.getLogger(__name__)


class PushDeliveryError(Exception):
    """A transient failure worth retrying."""


def create_notification(user, type, related_object_id=None, dedupe_key=None):
    """Create an in-app notification and queue its push. A repeated dedupe_key returns the existing row."""
    if dedupe_key:
        notification, created = Notification.objects.get_or_create(
            dedupe_key=dedupe_key,
            defaults={'user': user, 'type': type, 'related_object_id': related_object_id},
        )
    else:
        notification, created = (
            Notification.objects.create(user=user, type=type, related_object_id=related_object_id),
            True,
        )
    if created:
        _queue_push(notification)
    return notification


def _queue_push(notification):
    from .tasks import send_push

    def enqueue():
        try:
            send_push.delay(notification.pk)
        except Exception:  # a broker outage must never break the business operation
            logger.exception('Could not queue push for notification %s', notification.pk)

    transaction.on_commit(enqueue)


def mark_delivery(notification_id, status):
    Notification.objects.filter(pk=notification_id).update(delivery_status=status, modified_at=timezone.now())


def deliver_push(notification_id):
    """Send to every device of the recipient. Safe to call repeatedly: only PENDING rows are attempted."""
    notification = Notification.objects.filter(
        pk=notification_id, delivery_status=Notification.DeliveryStatus.PENDING
    ).first()
    if notification is None:
        return
    subscriptions = list(PushSubscription.objects.filter(user_id=notification.user_id))
    if not push.push_enabled() or not subscriptions:
        mark_delivery(notification.pk, Notification.DeliveryStatus.SKIPPED)
        return

    title, body = message_for(notification.type)
    payload = {
        'title': title,
        'body': body,
        'type': notification.type,
        'related_object_id': notification.related_object_id,
        'notification_id': notification.pk,
    }
    delivered, failed = 0, 0
    for subscription in subscriptions:
        try:
            push.send_web_push(subscription, payload)
            delivered += 1
        except push.SubscriptionGone:
            subscription.delete()
        except Exception:
            logger.warning('Push to subscription %s failed', subscription.pk, exc_info=True)
            failed += 1
    if delivered:
        mark_delivery(notification.pk, Notification.DeliveryStatus.SENT)
    elif failed:
        raise PushDeliveryError(f'{failed} push deliveries failed')
    else:
        mark_delivery(notification.pk, Notification.DeliveryStatus.SKIPPED)


def mark_read(user, notification_id):
    notification = Notification.objects.filter(pk=notification_id, user=user).first()
    if notification is None:
        return None
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=['read_at', 'modified_at'])
    return notification


def save_subscription(user, *, endpoint, p256dh, auth):
    """Register (or move to this user) a device endpoint; idempotent per endpoint."""
    subscription, _ = PushSubscription.objects.update_or_create(
        endpoint=endpoint, defaults={'user': user, 'p256dh': p256dh, 'auth': auth}
    )
    return subscription

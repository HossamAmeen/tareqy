import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

logger = logging.getLogger(__name__)


def push_enabled():
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


class SubscriptionGone(Exception):
    """The push service says this subscription no longer exists (404/410)."""


def send_web_push(subscription, payload):
    """Send one payload to one subscription. Raises SubscriptionGone for dead endpoints."""
    try:
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={'sub': f'mailto:{settings.VAPID_CLAIMS_EMAIL}'},
            ttl=3600,
        )
    except WebPushException as exc:
        status = getattr(exc.response, 'status_code', None)
        if status in (404, 410):
            raise SubscriptionGone from exc
        raise

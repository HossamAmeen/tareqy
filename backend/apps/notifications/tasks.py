import logging

from celery import shared_task

from . import services

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_push(self, notification_id):
    """Deliver a notification by Web Push. Failures only affect the delivery status, never business state."""
    try:
        services.deliver_push(notification_id)
    except services.PushDeliveryError as exc:
        if self.request.retries >= self.max_retries:
            services.mark_delivery(notification_id, 'FAILED')
            return
        raise self.retry(exc=exc) from exc
    except Exception:
        logger.exception('Unexpected push failure for notification %s', notification_id)

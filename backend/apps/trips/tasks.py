from celery import shared_task

from . import services


@shared_task
def expire_requests():
    """Thin wrapper: business logic lives in services.expire_due_requests (idempotent)."""
    return services.expire_due_requests()

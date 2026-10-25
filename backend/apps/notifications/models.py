from django.conf import settings
from django.db import models

from common.models import BaseModel


class Notification(BaseModel):
    class DeliveryStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'
        SKIPPED = 'SKIPPED', 'Skipped'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=40)
    related_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    delivery_status = models.CharField(max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    read_at = models.DateTimeField(null=True, blank=True)
    # Prevents duplicate notifications for the same event.
    dedupe_key = models.CharField(max_length=120, null=True, blank=True, unique=True)

    class Meta:
        ordering = ['-created_at']


class PushSubscription(BaseModel):
    """A browser Web Push endpoint registered by a user (one user may have several devices)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.areas.models import Area
from common.models import BaseModel


class TripRequest(BaseModel):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        EXPIRED = 'EXPIRED', 'Expired'

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='trip_requests')
    pickup_area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='+')
    destination_area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='+')
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True)
    preferred_pickup_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    expires_at = models.DateTimeField(db_index=True)

    @property
    def effective_status(self):
        """OPEN requests past their expiry read as EXPIRED even before the expiry job has run."""
        if self.status == self.Status.OPEN and self.expires_at <= timezone.now():
            return self.Status.EXPIRED
        return self.status

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=~Q(pickup_area=F('destination_area')), name='request_pickup_ne_destination'
            ),
        ]


class DriverInterest(BaseModel):
    class Status(models.TextChoices):
        INTERESTED = 'INTERESTED', 'Interested'
        CONTACTED = 'CONTACTED', 'Contacted'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
        DECLINED = 'DECLINED', 'Declined'
        SELECTED = 'SELECTED', 'Selected'

    trip_request = models.ForeignKey(TripRequest, on_delete=models.CASCADE, related_name='interests')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='interests')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.INTERESTED)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['trip_request', 'driver'], name='uniq_interest_per_request_driver'),
        ]


class Trip(BaseModel):
    class Status(models.TextChoices):
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        IN_PROGRESS = 'IN_PROGRESS', 'In progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    trip_request = models.ForeignKey(TripRequest, on_delete=models.PROTECT, related_name='trips')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='trips')
    agreed_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    pickup_details = models.CharField(max_length=300, blank=True)
    scheduled_pickup_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CONFIRMED, db_index=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    # Idempotency-Key of the confirm call, so a retried confirmation returns this trip instead of a conflict.
    confirm_idempotency_key = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            # At most one non-cancelled trip per request, enforced by the database.
            models.UniqueConstraint(
                fields=['trip_request'], condition=~Q(status='CANCELLED'), name='one_active_trip_per_request'
            ),
        ]


class StatusEvent(models.Model):
    """Append-only audit log of status transitions (requests, interests, trips)."""

    object_type = models.CharField(max_length=30)
    object_id = models.PositiveBigIntegerField()
    from_status = models.CharField(max_length=12, blank=True)
    to_status = models.CharField(max_length=12)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [models.Index(fields=['object_type', 'object_id'])]

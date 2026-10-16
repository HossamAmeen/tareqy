from django.conf import settings
from django.db import models

from common.models import BaseModel


class Report(BaseModel):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        REVIEWING = 'REVIEWING', 'Reviewing'
        RESOLVED = 'RESOLVED', 'Resolved'
        DISMISSED = 'DISMISSED', 'Dismissed'

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_made')
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reports_received'
    )
    trip = models.ForeignKey('trips.Trip', null=True, blank=True, on_delete=models.SET_NULL, related_name='reports')
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    class Meta:
        ordering = ['-created_at']

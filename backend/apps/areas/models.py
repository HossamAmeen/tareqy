from django.db import models

from common.models import BaseModel


class Area(BaseModel):
    name = models.CharField(max_length=120, unique=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class AreaCompatibility(BaseModel):
    """A driver in `origin` heading to `driver_destination` can take a passenger going to `request_destination`.

    Identical destinations are always compatible (handled by the matching service); rows here cover
    destinations that lie on the driver's way.
    """

    origin = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='+')
    driver_destination = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='+')
    request_destination = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='+')

    class Meta:
        verbose_name_plural = 'area compatibilities'
        constraints = [
            models.UniqueConstraint(
                fields=['origin', 'driver_destination', 'request_destination'], name='uniq_area_compatibility'
            ),
        ]

    def __str__(self):
        return f'{self.origin} | {self.driver_destination} -> {self.request_destination}'

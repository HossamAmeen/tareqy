from .models import StatusEvent


def record_status_event(obj, from_status, to_status, actor=None):
    """Log a status transition for a TripRequest, DriverInterest or Trip."""
    return StatusEvent.objects.create(
        object_type=type(obj).__name__,
        object_id=obj.pk,
        from_status=from_status or '',
        to_status=to_status,
        actor=actor,
    )

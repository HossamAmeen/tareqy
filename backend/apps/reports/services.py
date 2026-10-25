from django.db.models import Q

from apps.trips.models import Trip
from common.exceptions import BusinessRuleError

from .models import Report


def create_report(reporter, *, reason, trip_id=None, related_user=None):
    """File a report about a trip (the other party is derived) or about a user the reporter has shared a trip with."""
    trip = None
    if trip_id is not None:
        trip = Trip.objects.select_related('trip_request').filter(pk=trip_id).first()
        parties = (trip.driver_id, trip.trip_request.customer_id) if trip else ()
        if trip is None or reporter.pk not in parties:
            raise BusinessRuleError('Trip not found.')
        related_user_id = parties[0] if reporter.pk == parties[1] else parties[1]
    elif related_user is not None:
        shared = Trip.objects.filter(
            Q(driver=reporter, trip_request__customer=related_user)
            | Q(driver=related_user, trip_request__customer=reporter)
        ).exists()
        if related_user.pk == reporter.pk or not shared:
            raise BusinessRuleError('You can only report someone you have a trip with.')
        related_user_id = related_user.pk
    else:
        raise BusinessRuleError('Choose a trip or a user to report.')
    return Report.objects.create(reporter=reporter, related_user_id=related_user_id, trip=trip, reason=reason)

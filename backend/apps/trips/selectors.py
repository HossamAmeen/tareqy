from django.db.models import Prefetch

from .models import DriverInterest, Trip, TripRequest

# Interests a customer can see (and whose driver contact details are revealed to them).
VISIBLE_INTEREST_STATUSES = (
    DriverInterest.Status.INTERESTED,
    DriverInterest.Status.CONTACTED,
    DriverInterest.Status.SELECTED,
)


def customer_requests(user):
    return (
        TripRequest.objects.filter(customer=user)
        .select_related('pickup_area', 'destination_area')
        .prefetch_related(Prefetch('trips', queryset=Trip.objects.select_related('driver')))
    )


def request_interests(trip_request):
    return trip_request.interests.filter(status__in=VISIBLE_INTEREST_STATUSES).select_related('driver')


def driver_interests(user):
    return (
        DriverInterest.objects.filter(driver=user)
        .exclude(status=DriverInterest.Status.WITHDRAWN)
        .select_related('trip_request__pickup_area', 'trip_request__destination_area', 'trip_request__customer')
        .prefetch_related(Prefetch('trip_request__trips', queryset=Trip.objects.exclude(status='CANCELLED')))
        .order_by('-modified_at')
    )

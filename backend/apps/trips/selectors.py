from .models import TripRequest


def customer_requests(user):
    return TripRequest.objects.filter(customer=user).select_related('pickup_area', 'destination_area')

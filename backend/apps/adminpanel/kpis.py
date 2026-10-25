"""KPI definitions (business doc section 17). Formulas are documented in docs/kpis.md.

Eligible requests: created inside the window, not from test accounts (unless `include_test`).
Rates about outcomes use *decided* requests (confirmed, cancelled or expired) so that requests still
waiting for drivers do not drag the rate down. A rate is None when its denominator is zero.
"""

from datetime import timedelta

from django.db.models import Count, Min
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.accounts.models import DriverProfile
from apps.trips.models import DriverInterest, Trip, TripRequest


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _avg_seconds(deltas):
    deltas = list(deltas)
    return round(sum(d.total_seconds() for d in deltas) / len(deltas)) if deltas else None


def compute_kpis(days=30, include_test=False, now=None):
    now = now or timezone.now()
    since = now - timedelta(days=days)

    requests = TripRequest.objects.filter(created_at__gte=since)
    trips = Trip.objects.filter(created_at__gte=since)
    interests = DriverInterest.objects.filter(trip_request__created_at__gte=since)
    drivers = DriverProfile.objects.all()
    if not include_test:
        requests = requests.filter(customer__is_test_account=False)
        trips = trips.filter(trip_request__customer__is_test_account=False)
        interests = interests.filter(trip_request__customer__is_test_account=False)
        drivers = drivers.filter(user__is_test_account=False)

    eligible = requests.count()
    confirmed = requests.filter(status=TripRequest.Status.CONFIRMED).count()
    cancelled = requests.filter(status=TripRequest.Status.CANCELLED).count()
    expired = (
        requests.filter(status=TripRequest.Status.EXPIRED).count()
        + requests.filter(status=TripRequest.Status.OPEN, expires_at__lte=now).count()
    )
    open_now = requests.filter(status=TripRequest.Status.OPEN, expires_at__gt=now).count()
    decided = confirmed + cancelled + expired

    with_interest = requests.filter(interests__isnull=False).distinct().count()

    first_interest = requests.annotate(first=Min('interests__created_at')).filter(first__isnull=False)
    to_first_interest = (r.first - r.created_at for r in first_interest.only('created_at'))

    confirmed_trips = trips.exclude(confirmed_at__isnull=True)
    to_confirmation = (
        t.confirmed_at - t.trip_request.created_at for t in confirmed_trips.select_related('trip_request')
    )

    total_trips = trips.count()
    cancelled_trips = trips.filter(status=Trip.Status.CANCELLED).count()

    per_customer = requests.values('customer').annotate(n=Count('id'))
    customers = per_customer.count()
    returning = per_customer.filter(n__gte=2).count()

    daily = requests.annotate(day=TruncDate('created_at')).values('day').annotate(n=Count('id')).order_by('day')

    return {
        'window_days': days,
        'include_test': include_test,
        'requests_published': eligible,
        'requests_per_day': [{'date': row['day'].isoformat(), 'count': row['n']} for row in daily],
        'open_now': open_now,
        'interest_rate': _rate(with_interest, eligible),
        'confirmation_rate': _rate(confirmed, decided),
        'expired_rate': _rate(expired, decided),
        'cancelled_before_confirmation_rate': _rate(cancelled, decided),
        'cancelled_after_confirmation_rate': _rate(cancelled_trips, total_trips),
        'avg_seconds_to_first_interest': _avg_seconds(to_first_interest),
        'avg_seconds_to_confirmation': _avg_seconds(to_confirmation),
        'active_drivers_24h': drivers.filter(location_updated_at__gte=now - timedelta(hours=24)).count(),
        'customers': customers,
        'returning_customers': returning,
        'returning_customer_rate': _rate(returning, customers),
    }

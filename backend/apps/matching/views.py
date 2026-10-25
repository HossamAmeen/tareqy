from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.accounts import services as account_services
from apps.accounts.permissions import IsDriver
from apps.trips import selectors as trip_selectors
from apps.trips.models import DriverInterest
from apps.trips.serializers import DriverInterestSerializer
from common.responses import success_response
from common.throttling import LocationRateThrottle

from . import services
from .serializers import (
    DriverLocationSerializer,
    DriverProfileSerializer,
    DriverProfileWriteSerializer,
    MatchedRequestSerializer,
)


class DriverProfileView(APIView):
    permission_classes = [IsDriver]

    @extend_schema(responses=DriverProfileSerializer)
    def get(self, request):
        return success_response(DriverProfileSerializer(account_services.get_driver_profile(request.user)).data)

    @extend_schema(request=DriverProfileWriteSerializer, responses=DriverProfileSerializer)
    def patch(self, request):
        serializer = DriverProfileWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = account_services.update_driver_profile(request.user, **serializer.validated_data)
        return success_response(DriverProfileSerializer(profile).data, message='Driver mode updated.')


class DriverLocationView(APIView):
    permission_classes = [IsDriver]
    throttle_classes = [LocationRateThrottle]

    @extend_schema(request=DriverLocationSerializer, responses=DriverProfileSerializer)
    def post(self, request):
        serializer = DriverLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = account_services.update_driver_location(request.user, **serializer.validated_data)
        return success_response(DriverProfileSerializer(profile).data, message='Location updated.')


class DriverRequestListView(APIView):
    """Open requests that are candidates for the current driver (estimated matches)."""

    permission_classes = [IsDriver]

    @extend_schema(responses=MatchedRequestSerializer(many=True))
    def get(self, request):
        requests = services.matching_requests(request.user)
        interests = dict(
            DriverInterest.objects.filter(driver=request.user, trip_request__in=requests).values_list(
                'trip_request_id', 'status'
            )
        )
        data = MatchedRequestSerializer(requests, many=True, context={'interests': interests}).data
        return success_response(data)


class InterestView(APIView):
    permission_classes = [IsDriver]

    @extend_schema(request=None, responses={200: None, 201: None})
    def post(self, request, pk):
        interest, created = services.express_interest(request.user, pk)
        return success_response(
            {'status': interest.status},
            message='Interest recorded.' if created else 'Interest already recorded.',
            status_code=201 if created else 200,
        )

    @extend_schema(request=None, responses={200: None})
    def delete(self, request, pk):
        interest = services.withdraw_interest(request.user, pk)
        return success_response({'status': interest.status}, message='Interest withdrawn.')


class DriverInterestListView(APIView):
    """The driver's own interests with outcome, agreement and (once contact began) the customer's phone."""

    permission_classes = [IsDriver]

    @extend_schema(responses=DriverInterestSerializer(many=True))
    def get(self, request):
        interests = trip_selectors.driver_interests(request.user)
        return success_response(DriverInterestSerializer(interests, many=True).data)

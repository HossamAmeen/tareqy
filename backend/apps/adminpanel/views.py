from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin
from apps.reports.models import Report
from apps.trips.models import StatusEvent, Trip, TripRequest
from common.responses import success_response
from common.throttling import SensitiveRateThrottle
from common.views import EnvelopeMixin

from . import services
from .kpis import compute_kpis
from .serializers import (
    AdminReportSerializer,
    AdminRequestSerializer,
    AdminTripSerializer,
    AdminUserSerializer,
    ReportReviewSerializer,
    StatusEventSerializer,
)


class AdminReadViewSet(EnvelopeMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Staff-only, read access with a status history on the detail view."""

    permission_classes = [IsAdmin]
    history_type = ''

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        data = dict(self.get_serializer(obj).data)
        if self.history_type:
            events = StatusEvent.objects.filter(object_type=self.history_type, object_id=obj.pk).select_related('actor')
            data['history'] = StatusEventSerializer(events, many=True).data
        return success_response(data)


class AdminUserViewSet(AdminReadViewSet):
    serializer_class = AdminUserSerializer
    history_type = 'User'

    def get_queryset(self):
        queryset = User.objects.select_related('driver_profile').order_by('-created_at')
        params = self.request.query_params
        if search := params.get('search'):
            queryset = queryset.filter(Q(phone__icontains=search) | Q(name__icontains=search))
        if params.get('role') == 'driver':
            queryset = queryset.filter(is_driver=True)
        elif params.get('role') == 'customer':
            queryset = queryset.filter(is_customer=True)
        if status := params.get('status'):
            queryset = queryset.filter(account_status=status)
        return queryset

    def _respond(self, user, message):
        user = self.get_queryset().get(pk=user.pk)
        return success_response(AdminUserSerializer(user).data, message=message)

    @extend_schema(request=None, responses={200: AdminUserSerializer})
    @action(detail=True, methods=['post'], throttle_classes=[SensitiveRateThrottle])
    def suspend(self, request, pk=None):
        user = services.set_account_status(self.get_object(), User.AccountStatus.SUSPENDED, request.user)
        return self._respond(user, 'Account suspended.')

    @extend_schema(request=None, responses={200: AdminUserSerializer})
    @action(detail=True, methods=['post'], throttle_classes=[SensitiveRateThrottle])
    def activate(self, request, pk=None):
        user = services.set_account_status(self.get_object(), User.AccountStatus.ACTIVE, request.user)
        return self._respond(user, 'Account activated.')

    @extend_schema(request=None, responses={200: AdminUserSerializer})
    @action(detail=True, methods=['post'], url_path='verify-driver', throttle_classes=[SensitiveRateThrottle])
    def verify_driver(self, request, pk=None):
        user = self.get_object()
        services.set_driver_verified(user, True, request.user)
        return self._respond(user, 'Driver verified.')

    @extend_schema(request=None, responses={200: AdminUserSerializer})
    @action(detail=True, methods=['post'], url_path='unverify-driver', throttle_classes=[SensitiveRateThrottle])
    def unverify_driver(self, request, pk=None):
        user = self.get_object()
        services.set_driver_verified(user, False, request.user)
        return self._respond(user, 'Driver verification removed.')


class AdminRequestViewSet(AdminReadViewSet):
    serializer_class = AdminRequestSerializer
    history_type = 'TripRequest'

    def get_queryset(self):
        queryset = (
            TripRequest.objects.select_related('customer', 'pickup_area', 'destination_area')
            .annotate(interest_count=Count('interests'))
            .order_by('-created_at')
        )
        if status := self.request.query_params.get('status'):
            queryset = queryset.filter(status=status)
        return queryset


class AdminTripViewSet(AdminReadViewSet):
    serializer_class = AdminTripSerializer
    history_type = 'Trip'

    def get_queryset(self):
        queryset = Trip.objects.select_related(
            'driver', 'trip_request__customer', 'trip_request__pickup_area', 'trip_request__destination_area'
        ).order_by('-created_at')
        if status := self.request.query_params.get('status'):
            queryset = queryset.filter(status=status)
        return queryset


class AdminReportViewSet(AdminReadViewSet):
    serializer_class = AdminReportSerializer
    history_type = 'Report'

    def get_queryset(self):
        queryset = Report.objects.select_related('reporter', 'related_user').order_by('-created_at')
        if status := self.request.query_params.get('status'):
            queryset = queryset.filter(status=status)
        return queryset

    @extend_schema(request=ReportReviewSerializer, responses={200: AdminReportSerializer})
    @action(detail=True, methods=['post'], throttle_classes=[SensitiveRateThrottle])
    def review(self, request, pk=None):
        serializer = ReportReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = services.review_report(
            self.get_object(), serializer.validated_data['status'], serializer.validated_data['note'], request.user
        )
        return success_response(AdminReportSerializer(report).data, message='Report updated.')


class KpiView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(responses={200: None})
    def get(self, request):
        try:
            days = min(max(int(request.query_params.get('days', 30)), 1), 365)
        except ValueError:
            days = 30
        include_test = request.query_params.get('include_test') == 'true'
        return success_response(compute_kpis(days=days, include_test=include_test))

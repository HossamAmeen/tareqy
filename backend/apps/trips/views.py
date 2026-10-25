from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action

from apps.accounts.permissions import IsCustomer
from common.responses import success_response
from common.views import EnvelopeMixin

from . import selectors, services
from .serializers import (
    ConfirmSerializer,
    InterestSerializer,
    TripRequestSerializer,
    TripRequestWriteSerializer,
    TripSerializer,
)


class TripRequestViewSet(
    EnvelopeMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """The authenticated customer's own trip requests."""

    permission_classes = [IsCustomer]
    serializer_class = TripRequestSerializer

    def get_queryset(self):
        return selectors.customer_requests(self.request.user)

    @extend_schema(request=TripRequestWriteSerializer, responses={201: TripRequestSerializer})
    def create(self, request):
        serializer = TripRequestWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip_request = services.create_request(request.user, **serializer.validated_data)
        return success_response(TripRequestSerializer(trip_request).data, message='Request created.', status_code=201)

    @extend_schema(request=TripRequestWriteSerializer, responses={200: TripRequestSerializer})
    def partial_update(self, request, pk=None):
        trip_request = self.get_object()
        serializer = TripRequestWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        trip_request = services.update_request(trip_request, request.user, **serializer.validated_data)
        return success_response(TripRequestSerializer(trip_request).data, message='Request updated.')

    @extend_schema(request=None, responses={200: TripRequestSerializer})
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        trip_request = services.cancel_request(self.get_object(), request.user)
        return success_response(TripRequestSerializer(trip_request).data, message='Request cancelled.')

    @extend_schema(responses=InterestSerializer(many=True))
    @action(detail=True, methods=['get'], pagination_class=None)
    def interests(self, request, pk=None):
        interests = selectors.request_interests(self.get_object())
        return success_response(InterestSerializer(interests, many=True).data)

    @extend_schema(request=None, responses={200: InterestSerializer})
    @action(detail=True, methods=['post'], url_path=r'interests/(?P<interest_id>\d+)/contacted')
    def contacted(self, request, pk=None, interest_id=None):
        interest = services.mark_contacted(self.get_object(), int(interest_id), request.user)
        return success_response(InterestSerializer(interest).data, message='Marked as contacted.')

    @extend_schema(request=ConfirmSerializer, responses={200: TripSerializer, 201: TripSerializer})
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm one driver. Send an `Idempotency-Key` header so a retried call returns the same trip."""
        serializer = ConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        trip, created = services.confirm_trip(
            self.get_object(),
            request.user,
            interest_id=data['interest'],
            agreed_price=data['agreed_price'],
            pickup_details=data.get('pickup_details', ''),
            scheduled_pickup_at=data.get('scheduled_pickup_at'),
            idempotency_key=request.headers.get('Idempotency-Key', '')[:64],
        )
        return success_response(
            TripSerializer(trip, context={'role': 'customer'}).data,
            message='Trip confirmed.' if created else 'Trip already confirmed.',
            status_code=201 if created else 200,
        )


class TripViewSet(EnvelopeMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Trips the user takes part in, as customer or as driver."""

    serializer_class = TripSerializer

    def get_queryset(self):
        return selectors.user_trips(self.request.user)

    @staticmethod
    def _role(user, trip):
        return 'driver' if trip is not None and trip.driver_id == user.pk else 'customer'

    def _render(self, trip, message):
        return success_response(
            TripSerializer(trip, context={'role': self._role(self.request.user, trip)}).data, message
        )

    def retrieve(self, request, *args, **kwargs):
        trip = self.get_object()
        return success_response(TripSerializer(trip, context={'role': self._role(request.user, trip)}).data)

    def list(self, request, *args, **kwargs):
        rows = [TripSerializer(t, context={'role': self._role(request.user, t)}).data for t in self.get_queryset()]
        return success_response(rows)

    @extend_schema(request=None, responses={200: TripSerializer})
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        return self._render(services.start_trip(self.get_object(), request.user), 'Trip started.')

    @extend_schema(request=None, responses={200: TripSerializer})
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        return self._render(services.complete_trip(self.get_object(), request.user), 'Trip completed.')

    @extend_schema(request=None, responses={200: TripSerializer})
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        return self._render(services.cancel_trip(self.get_object(), request.user), 'Trip cancelled.')

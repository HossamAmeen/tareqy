from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action

from apps.accounts.permissions import IsCustomer
from common.responses import success_response
from common.views import EnvelopeMixin

from . import selectors, services
from .serializers import TripRequestSerializer, TripRequestWriteSerializer


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

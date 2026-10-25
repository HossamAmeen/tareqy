from rest_framework import serializers

from apps.areas.models import Area
from apps.areas.serializers import AreaSerializer

from .models import DriverInterest, Trip, TripRequest


class PersonSerializer(serializers.Serializer):
    """The other party in a trip. The phone is only ever serialised for a customer<->driver pair."""

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)


class TripSerializer(serializers.ModelSerializer):
    """A trip with its agreement. `context['role']` ('customer' | 'driver') decides who the counterpart is."""

    counterpart = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    pickup_area = AreaSerializer(source='trip_request.pickup_area', read_only=True)
    destination_area = AreaSerializer(source='trip_request.destination_area', read_only=True)

    class Meta:
        model = Trip
        fields = [
            'id',
            'trip_request',
            'role',
            'pickup_area',
            'destination_area',
            'status',
            'agreed_price',
            'pickup_details',
            'scheduled_pickup_at',
            'confirmed_at',
            'started_at',
            'completed_at',
            'cancelled_at',
            'counterpart',
        ]
        read_only_fields = fields

    def get_role(self, obj) -> str:
        return self.context.get('role', 'customer')

    def get_counterpart(self, obj):
        person = obj.driver if self.context.get('role') == 'customer' else obj.trip_request.customer
        return PersonSerializer(person).data


class InterestSerializer(serializers.ModelSerializer):
    driver = PersonSerializer(read_only=True)

    class Meta:
        model = DriverInterest
        fields = ['id', 'status', 'driver', 'created_at']
        read_only_fields = fields


class ConfirmSerializer(serializers.Serializer):
    interest = serializers.IntegerField()
    agreed_price = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    pickup_details = serializers.CharField(max_length=300, required=False, allow_blank=True)
    scheduled_pickup_at = serializers.DateTimeField(required=False, allow_null=True)


class DriverInterestSerializer(serializers.ModelSerializer):
    """The driver's view of one of their interests. The customer's phone appears only once contact began."""

    request = serializers.SerializerMethodField()
    trip = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()

    class Meta:
        model = DriverInterest
        fields = ['id', 'status', 'request', 'trip', 'customer_phone']
        read_only_fields = fields

    def get_request(self, obj):
        req = obj.trip_request
        return {
            'id': req.pk,
            'pickup_area': AreaSerializer(req.pickup_area).data,
            'destination_area': AreaSerializer(req.destination_area).data,
            'notes': req.notes,
            'status': req.effective_status,
            'expires_at': req.expires_at,
        }

    def get_trip(self, obj):
        if obj.status != DriverInterest.Status.SELECTED:
            return None
        trips = sorted(
            (t for t in obj.trip_request.trips.all() if t.driver_id == obj.driver_id),
            key=lambda t: (t.status == Trip.Status.CANCELLED, -t.pk),
        )
        trip = trips[0] if trips else None
        return TripSerializer(trip, context={'role': 'driver'}).data if trip else None

    def get_customer_phone(self, obj) -> str | None:
        if obj.status in (DriverInterest.Status.CONTACTED, DriverInterest.Status.SELECTED):
            return obj.trip_request.customer.phone
        return None


class TripRequestSerializer(serializers.ModelSerializer):
    pickup_area = AreaSerializer(read_only=True)
    destination_area = AreaSerializer(read_only=True)
    status = serializers.CharField(source='effective_status', read_only=True)
    pickup_location_is_precise = serializers.SerializerMethodField()
    trip = serializers.SerializerMethodField()

    class Meta:
        model = TripRequest
        fields = [
            'id',
            'pickup_area',
            'destination_area',
            'pickup_location_is_precise',
            'notes',
            'preferred_pickup_at',
            'status',
            'expires_at',
            'created_at',
            'trip',
        ]
        read_only_fields = fields

    def get_trip(self, obj):
        trips = sorted(obj.trips.all(), key=lambda t: (t.status == Trip.Status.CANCELLED, -t.pk))
        trip = trips[0] if trips else None
        return TripSerializer(trip, context={'role': 'customer'}).data if trip else None

    def get_pickup_location_is_precise(self, obj) -> bool:
        return obj.pickup_latitude is not None and obj.pickup_longitude is not None


class TripRequestWriteSerializer(serializers.Serializer):
    pickup_area = serializers.PrimaryKeyRelatedField(queryset=Area.objects.filter(is_active=True))
    destination_area = serializers.PrimaryKeyRelatedField(queryset=Area.objects.filter(is_active=True))
    notes = serializers.CharField(max_length=300, required=False, allow_blank=True)
    preferred_pickup_at = serializers.DateTimeField(required=False, allow_null=True)
    pickup_latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, min_value=-90, max_value=90
    )
    pickup_longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, min_value=-180, max_value=180
    )

    def validate(self, attrs):
        has_lat, has_lng = 'pickup_latitude' in attrs, 'pickup_longitude' in attrs
        if has_lat != has_lng:
            raise serializers.ValidationError('Provide both pickup_latitude and pickup_longitude.')
        return attrs

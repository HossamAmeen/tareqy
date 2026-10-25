from rest_framework import serializers

from apps.accounts.models import DriverProfile
from apps.areas.models import Area
from apps.areas.serializers import AreaSerializer
from apps.trips.models import TripRequest

from . import services


class DriverProfileSerializer(serializers.ModelSerializer):
    current_area = AreaSerializer(read_only=True)
    destination_area = serializers.SerializerMethodField()
    destination_expires_at = serializers.SerializerMethodField()
    location_status = serializers.SerializerMethodField()

    class Meta:
        model = DriverProfile
        fields = [
            'availability_status',
            'is_verified',
            'current_area',
            'location_updated_at',
            'location_status',
            'destination_area',
            'destination_expires_at',
        ]
        read_only_fields = fields

    def get_destination_area(self, obj):
        return AreaSerializer(obj.destination_area).data if services.destination_is_active(obj) else None

    def get_destination_expires_at(self, obj):
        return obj.destination_expires_at if services.destination_is_active(obj) else None

    def get_location_status(self, obj) -> str:
        if obj.location_updated_at is None:
            return 'none'
        return 'fresh' if services.location_is_fresh(obj) else 'stale'


class DriverProfileWriteSerializer(serializers.Serializer):
    availability_status = serializers.ChoiceField(choices=DriverProfile.Availability.choices, required=False)
    destination_area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.filter(is_active=True), required=False, allow_null=True
    )
    destination_ttl_minutes = serializers.IntegerField(required=False, min_value=5, max_value=720)


class DriverLocationSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-90, max_value=90)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-180, max_value=180)
    current_area = serializers.PrimaryKeyRelatedField(queryset=Area.objects.filter(is_active=True), required=False)


class MatchedRequestSerializer(serializers.ModelSerializer):
    """A request as shown to a candidate driver: no customer identity or contact details."""

    pickup_area = AreaSerializer(read_only=True)
    destination_area = AreaSerializer(read_only=True)
    match_type = serializers.SerializerMethodField()
    my_interest = serializers.SerializerMethodField()

    class Meta:
        model = TripRequest
        fields = [
            'id',
            'pickup_area',
            'destination_area',
            'notes',
            'preferred_pickup_at',
            'expires_at',
            'match_type',
            'my_interest',
        ]
        read_only_fields = fields

    def get_match_type(self, obj) -> str:
        return 'estimated'

    def get_my_interest(self, obj) -> str | None:
        return self.context.get('interests', {}).get(obj.pk)

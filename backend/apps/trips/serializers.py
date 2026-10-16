from rest_framework import serializers

from apps.areas.models import Area
from apps.areas.serializers import AreaSerializer

from .models import TripRequest


class TripRequestSerializer(serializers.ModelSerializer):
    pickup_area = AreaSerializer(read_only=True)
    destination_area = AreaSerializer(read_only=True)
    status = serializers.CharField(source='effective_status', read_only=True)
    pickup_location_is_precise = serializers.SerializerMethodField()

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
        ]
        read_only_fields = fields

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

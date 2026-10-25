from rest_framework import serializers

from apps.accounts.models import User
from apps.reports.models import Report
from apps.trips.models import StatusEvent, Trip, TripRequest


class AdminUserSerializer(serializers.ModelSerializer):
    is_verified = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'phone',
            'name',
            'account_status',
            'is_customer',
            'is_driver',
            'is_staff',
            'is_test_account',
            'is_verified',
            'created_at',
        ]
        read_only_fields = fields

    def get_is_verified(self, obj) -> bool | None:
        profile = getattr(obj, 'driver_profile', None)
        return profile.is_verified if obj.is_driver and profile else (False if obj.is_driver else None)


class StatusEventSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = StatusEvent
        fields = ['from_status', 'to_status', 'actor', 'created_at']
        read_only_fields = fields

    def get_actor(self, obj) -> str | None:
        return obj.actor.phone if obj.actor else None


class AdminRequestSerializer(serializers.ModelSerializer):
    customer = serializers.CharField(source='customer.phone')
    pickup_area = serializers.CharField(source='pickup_area.name')
    destination_area = serializers.CharField(source='destination_area.name')
    status = serializers.CharField(source='effective_status')
    interest_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TripRequest
        fields = [
            'id',
            'customer',
            'pickup_area',
            'destination_area',
            'status',
            'expires_at',
            'created_at',
            'interest_count',
        ]
        read_only_fields = fields


class AdminTripSerializer(serializers.ModelSerializer):
    customer = serializers.CharField(source='trip_request.customer.phone')
    driver = serializers.CharField(source='driver.phone')
    pickup_area = serializers.CharField(source='trip_request.pickup_area.name')
    destination_area = serializers.CharField(source='trip_request.destination_area.name')

    class Meta:
        model = Trip
        fields = [
            'id',
            'trip_request',
            'customer',
            'driver',
            'pickup_area',
            'destination_area',
            'status',
            'agreed_price',
            'confirmed_at',
            'started_at',
            'completed_at',
            'cancelled_at',
        ]
        read_only_fields = fields


class AdminReportSerializer(serializers.ModelSerializer):
    reporter = serializers.CharField(source='reporter.phone')
    related_user = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id',
            'reporter',
            'related_user',
            'trip',
            'reason',
            'status',
            'resolution_note',
            'resolved_at',
            'created_at',
        ]
        read_only_fields = fields

    def get_related_user(self, obj) -> dict | None:
        return {'id': obj.related_user_id, 'phone': obj.related_user.phone} if obj.related_user else None


class ReportReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['REVIEWING', 'RESOLVED', 'DISMISSED'])
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')

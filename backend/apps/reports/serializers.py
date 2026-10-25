from rest_framework import serializers

from .models import Report


class ReportCreateSerializer(serializers.Serializer):
    trip = serializers.IntegerField(required=False)
    related_user = serializers.IntegerField(required=False)
    reason = serializers.CharField(min_length=5, max_length=1000)


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'trip', 'status', 'created_at']
        read_only_fields = fields

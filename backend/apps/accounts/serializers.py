from rest_framework import serializers

from .models import phone_validator


class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=16, validators=[phone_validator])


class OTPVerifySerializer(OTPRequestSerializer):
    code = serializers.CharField(max_length=10)


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    phone = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    is_customer = serializers.BooleanField(required=False)
    is_driver = serializers.BooleanField(required=False)
    account_status = serializers.CharField(read_only=True)

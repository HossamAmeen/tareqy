from rest_framework import serializers

from .messages import message_for
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'type', 'title', 'body', 'related_object_id', 'read_at', 'created_at']
        read_only_fields = fields

    def get_title(self, obj) -> str:
        return message_for(obj.type)[0]

    def get_body(self, obj) -> str:
        return message_for(obj.type)[1]


class PushSubscriptionSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2000)
    p256dh = serializers.CharField(max_length=255)
    auth = serializers.CharField(max_length=255)


class PushUnsubscribeSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2000)

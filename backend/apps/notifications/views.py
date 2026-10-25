from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from common.exceptions import BusinessRuleError
from common.responses import success_response

from . import push, services
from .models import Notification, PushSubscription
from .serializers import NotificationSerializer, PushSubscriptionSerializer, PushUnsubscribeSerializer

LIST_LIMIT = 50


class NotificationListView(APIView):
    """The in-app notification centre: the fallback that never depends on push delivery."""

    @extend_schema(responses=NotificationSerializer(many=True))
    def get(self, request):
        queryset = Notification.objects.filter(user=request.user)
        unread = queryset.filter(read_at__isnull=True).count()
        data = NotificationSerializer(queryset[:LIST_LIMIT], many=True).data
        return success_response({'unread_count': unread, 'results': data})


class NotificationReadView(APIView):
    @extend_schema(request=None, responses=NotificationSerializer)
    def post(self, request, pk):
        notification = services.mark_read(request.user, pk)
        if notification is None:
            raise BusinessRuleError('Notification not found.')
        return success_response(NotificationSerializer(notification).data)


class PushPublicKeyView(APIView):
    @extend_schema(responses={200: None})
    def get(self, request):
        return success_response({'enabled': push.push_enabled(), 'public_key': settings.VAPID_PUBLIC_KEY})


class PushSubscriptionView(APIView):
    @extend_schema(request=PushSubscriptionSerializer, responses={200: None})
    def post(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.save_subscription(request.user, **serializer.validated_data)
        return success_response(message='Subscribed.')

    @extend_schema(request=PushUnsubscribeSerializer, responses={200: None})
    def delete(self, request):
        serializer = PushUnsubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PushSubscription.objects.filter(user=request.user, endpoint=serializer.validated_data['endpoint']).delete()
        return success_response(message='Unsubscribed.')

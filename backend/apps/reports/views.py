from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from common.responses import success_response
from common.throttling import SensitiveRateThrottle

from . import services
from .serializers import ReportCreateSerializer, ReportSerializer


class ReportCreateView(APIView):
    throttle_classes = [SensitiveRateThrottle]

    @extend_schema(request=ReportCreateSerializer, responses={201: ReportSerializer})
    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        related = get_user_model().objects.filter(pk=data['related_user']).first() if 'related_user' in data else None
        report = services.create_report(
            request.user, reason=data['reason'], trip_id=data.get('trip'), related_user=related
        )
        return success_response(ReportSerializer(report).data, message='Report received.', status_code=201)

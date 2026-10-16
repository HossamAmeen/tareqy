from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from common.responses import success_response
from common.throttling import AuthRateThrottle

from . import services
from .serializers import OTPRequestSerializer, OTPVerifySerializer, UserSerializer


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Password login (staff/admin). Customers and drivers use OTP."""

    throttle_classes = [AuthRateThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [AuthRateThrottle]


class OTPRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(request=OTPRequestSerializer, responses={200: None, 400: None, 429: None}, auth=[])
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_otp(serializer.validated_data['phone'])
        return success_response(message='Verification code sent.')


class OTPVerifyView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(request=OTPVerifySerializer, responses={200: None, 400: None, 429: None}, auth=[])
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, tokens = services.verify_otp(serializer.validated_data['phone'], serializer.validated_data['code'])
        return success_response({**tokens, 'user': UserSerializer(user).data}, message='Signed in.')


class MeView(APIView):
    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return success_response(UserSerializer(request.user).data)

    @extend_schema(request=UserSerializer, responses=UserSerializer)
    def patch(self, request):
        serializer = UserSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = services.update_profile(request.user, **serializer.validated_data)
        return success_response(UserSerializer(user).data, message='Profile updated.')

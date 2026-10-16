from django.urls import path

from . import views

urlpatterns = [
    path('auth/token/', views.ThrottledTokenObtainPairView.as_view(), name='token'),
    path('auth/token/refresh/', views.ThrottledTokenRefreshView.as_view(), name='token-refresh'),
    path('auth/otp/request/', views.OTPRequestView.as_view(), name='otp-request'),
    path('auth/otp/verify/', views.OTPVerifyView.as_view(), name='otp-verify'),
    path('me/', views.MeView.as_view(), name='me'),
]

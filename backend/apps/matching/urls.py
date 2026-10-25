from django.urls import path

from . import views

urlpatterns = [
    path('driver/profile/', views.DriverProfileView.as_view(), name='driver-profile'),
    path('driver/location/', views.DriverLocationView.as_view(), name='driver-location'),
    path('driver/requests/', views.DriverRequestListView.as_view(), name='driver-requests'),
    path('requests/<int:pk>/interest/', views.InterestView.as_view(), name='request-interest'),
]

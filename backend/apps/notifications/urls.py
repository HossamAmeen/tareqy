from django.urls import path

from . import views

urlpatterns = [
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/read/', views.NotificationReadView.as_view(), name='notification-read'),
    path('push/public-key/', views.PushPublicKeyView.as_view(), name='push-public-key'),
    path('push/subscription/', views.PushSubscriptionView.as_view(), name='push-subscription'),
]

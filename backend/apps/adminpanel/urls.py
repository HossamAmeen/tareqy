from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('users', views.AdminUserViewSet, basename='admin-user')
router.register('requests', views.AdminRequestViewSet, basename='admin-request')
router.register('trips', views.AdminTripViewSet, basename='admin-trip')
router.register('reports', views.AdminReportViewSet, basename='admin-report')

urlpatterns = [path('kpis/', views.KpiView.as_view(), name='admin-kpis'), *router.urls]

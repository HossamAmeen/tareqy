from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', include('apps.health.urls')),
    path('api/', include('apps.accounts.urls')),
    path('api/areas/', include('apps.areas.urls')),
    path('api/', include('apps.trips.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

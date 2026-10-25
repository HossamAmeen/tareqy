from rest_framework.routers import DefaultRouter

from .views import TripRequestViewSet, TripViewSet

router = DefaultRouter()
router.register('requests', TripRequestViewSet, basename='request')
router.register('trips', TripViewSet, basename='trip')

urlpatterns = router.urls

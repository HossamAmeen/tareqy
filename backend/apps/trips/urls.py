from rest_framework.routers import DefaultRouter

from .views import TripRequestViewSet

router = DefaultRouter()
router.register('requests', TripRequestViewSet, basename='request')

urlpatterns = router.urls

from rest_framework.generics import ListAPIView

from common.views import EnvelopeMixin

from .models import Area
from .serializers import AreaSerializer


class AreaListView(EnvelopeMixin, ListAPIView):
    serializer_class = AreaSerializer
    pagination_class = None
    queryset = Area.objects.filter(is_active=True)

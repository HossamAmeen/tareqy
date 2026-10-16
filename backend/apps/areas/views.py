from rest_framework.generics import ListAPIView

from .models import Area
from .serializers import AreaSerializer


class AreaListView(ListAPIView):
    serializer_class = AreaSerializer
    pagination_class = None
    queryset = Area.objects.filter(is_active=True)

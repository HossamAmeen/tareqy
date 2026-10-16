from django.urls import path

from .views import AreaListView

urlpatterns = [path('', AreaListView.as_view(), name='area-list')]

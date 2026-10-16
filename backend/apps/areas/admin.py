from django.contrib import admin

from .models import Area, AreaCompatibility


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)


@admin.register(AreaCompatibility)
class AreaCompatibilityAdmin(admin.ModelAdmin):
    list_display = ('origin', 'driver_destination', 'request_destination')

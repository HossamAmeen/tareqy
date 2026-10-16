from django.contrib import admin

from .models import DriverInterest, StatusEvent, Trip, TripRequest


@admin.register(TripRequest)
class TripRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'pickup_area', 'destination_area', 'status', 'expires_at')
    list_filter = ('status',)


@admin.register(DriverInterest)
class DriverInterestAdmin(admin.ModelAdmin):
    list_display = ('trip_request', 'driver', 'status')


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'trip_request', 'driver', 'status', 'agreed_price')
    list_filter = ('status',)


@admin.register(StatusEvent)
class StatusEventAdmin(admin.ModelAdmin):
    list_display = ('object_type', 'object_id', 'from_status', 'to_status', 'actor', 'created_at')
    list_filter = ('object_type',)

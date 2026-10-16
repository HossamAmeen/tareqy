from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'delivery_status', 'read_at', 'created_at')
    list_filter = ('type', 'delivery_status')

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import DriverProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone', 'name', 'account_status', 'is_customer', 'is_driver', 'is_staff')
    list_filter = ('account_status', 'is_customer', 'is_driver', 'is_staff')
    search_fields = ('phone', 'name')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Profile', {'fields': ('name', 'account_status', 'is_customer', 'is_driver')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = ((None, {'classes': ('wide',), 'fields': ('phone', 'password1', 'password2')}),)


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'availability_status', 'destination_area', 'location_updated_at')

from rest_framework.permissions import BasePermission


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_customer)


class IsDriver(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_driver)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_staff)

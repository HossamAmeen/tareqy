from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Object-level: obj.owner_field must equal the requesting user. Set `owner_field` on the view."""

    def has_object_permission(self, request, view, obj):
        return getattr(obj, getattr(view, 'owner_field', 'user'), None) == request.user

from .models import Notification


def create_notification(user, type, related_object_id=None, dedupe_key=None):
    """Create an in-app notification. A repeated dedupe_key returns the existing row (safe for retries)."""
    if dedupe_key:
        notification, _ = Notification.objects.get_or_create(
            dedupe_key=dedupe_key,
            defaults={'user': user, 'type': type, 'related_object_id': related_object_id},
        )
        return notification
    return Notification.objects.create(user=user, type=type, related_object_id=related_object_id)

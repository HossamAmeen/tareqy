from django.db import models
from django.utils import timezone

from .managers import ActiveManager, AllManager, DeletedManager


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # The first manager is the default one: active records only.
    objects = ActiveManager()
    deleted_objects = DeletedManager()
    all_objects = AllManager()

    class Meta:
        abstract = True

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at', 'modified_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at', 'modified_at'])

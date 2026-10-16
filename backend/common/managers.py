from django.db import models


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class DeletedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=False)


class AllManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()

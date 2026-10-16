from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_queryset(self):
        # Default manager hides soft-deleted users (also used by auth/JWT lookups).
        return super().get_queryset().filter(deleted_at__isnull=True)

    def _create(self, phone, password, **extra):
        if not phone:
            raise ValueError('Phone is required.')
        user = self.model(phone=phone, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra):
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._create(phone, password, **extra)

    def create_superuser(self, phone, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self._create(phone, password, **extra)

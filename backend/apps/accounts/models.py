from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models

from apps.areas.models import Area
from common.managers import AllManager, DeletedManager
from common.models import BaseModel

from .managers import UserManager

phone_validator = RegexValidator(r'^\+?[0-9]{8,15}$', 'Enter a valid phone number.')


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    class AccountStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    phone = models.CharField(max_length=16, unique=True, validators=[phone_validator])
    name = models.CharField(max_length=120, blank=True)
    account_status = models.CharField(max_length=12, choices=AccountStatus.choices, default=AccountStatus.ACTIVE)
    is_customer = models.BooleanField(default=True)
    is_driver = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    # Pilot/test accounts are excluded from KPIs.
    is_test_account = models.BooleanField(default=False)

    objects = UserManager()
    deleted_objects = DeletedManager()
    all_objects = AllManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    @property
    def is_active(self):
        return self.account_status == self.AccountStatus.ACTIVE and self.deleted_at is None

    def __str__(self):
        return self.phone


class DriverProfile(BaseModel):
    class Availability(models.TextChoices):
        OFFLINE = 'OFFLINE', 'Offline'
        AVAILABLE = 'AVAILABLE', 'Available'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='driver_profile')
    availability_status = models.CharField(max_length=10, choices=Availability.choices, default=Availability.OFFLINE)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_updated_at = models.DateTimeField(null=True, blank=True)
    current_area = models.ForeignKey(Area, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    destination_area = models.ForeignKey(Area, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    destination_expires_at = models.DateTimeField(null=True, blank=True)
    # Set by an admin after checking the driver's licence and vehicle (decision 1).
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Driver {self.user_id}'


class OTPCode(BaseModel):
    phone = models.CharField(max_length=16, db_index=True)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

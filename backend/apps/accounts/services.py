import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from common.exceptions import BusinessRuleError
from common.geo import haversine_km

from .models import DriverProfile, OTPCode, User
from .sms import send_sms


def _hash_code(phone, code):
    return hmac.new(settings.SECRET_KEY.encode(), f'{phone}:{code}'.encode(), hashlib.sha256).hexdigest()


def request_otp(phone):
    """Create and send a one-time code. Enforces a per-phone resend cooldown."""
    now = timezone.now()
    last = OTPCode.objects.filter(phone=phone).first()
    if last and now - last.created_at < timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS):
        raise BusinessRuleError('Please wait before requesting another code.')

    code = ''.join(secrets.choice('0123456789') for _ in range(settings.OTP_LENGTH))
    OTPCode.objects.create(
        phone=phone,
        code_hash=_hash_code(phone, code),
        expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
    )
    send_sms(phone, f'Fi Tariqi code: {code}')


def verify_otp(phone, code):
    """Validate the latest code, create the user on first login, and return (user, tokens)."""
    with transaction.atomic():
        now = timezone.now()
        otp = OTPCode.objects.select_for_update().filter(phone=phone, consumed_at__isnull=True).first()
        usable = otp is not None and otp.expires_at > now and otp.attempts < settings.OTP_MAX_ATTEMPTS
        matches = usable and hmac.compare_digest(otp.code_hash, _hash_code(phone, code))

        if usable and not matches:
            # Persist the failed attempt: it must survive, so raise only after the transaction commits.
            otp.attempts += 1
            otp.save(update_fields=['attempts', 'modified_at'])
        elif matches:
            otp.consumed_at = now
            otp.save(update_fields=['consumed_at', 'modified_at'])
            user = User.all_objects.filter(phone=phone).first()
            if user is None:
                user = User.objects.create_user(phone=phone)

    if not matches:
        raise BusinessRuleError('Invalid or expired code.')
    if user.account_status != User.AccountStatus.ACTIVE or user.deleted_at is not None:
        raise BusinessRuleError('This account is not allowed to sign in.')

    refresh = RefreshToken.for_user(user)
    return user, {'access': str(refresh.access_token), 'refresh': str(refresh)}


@transaction.atomic
def update_profile(user, *, name=None, is_customer=None, is_driver=None):
    if name is not None:
        user.name = name
    if is_customer is not None:
        user.is_customer = is_customer
    if is_driver is not None:
        user.is_driver = is_driver
    if not (user.is_customer or user.is_driver):
        raise BusinessRuleError('At least one role (customer or driver) must be enabled.')
    user.save()
    if user.is_driver:
        DriverProfile.objects.get_or_create(user=user)
    return user


def get_driver_profile(user):
    return DriverProfile.objects.select_related('current_area', 'destination_area').get_or_create(user=user)[0]


_UNSET = object()


@transaction.atomic
def update_driver_profile(user, *, availability_status=None, destination_area=_UNSET, destination_ttl_minutes=None):
    """Toggle availability and/or set (or clear, with None) the driver's time-limited destination."""
    profile = DriverProfile.objects.select_for_update().get_or_create(user=user)[0]
    if availability_status is not None:
        profile.availability_status = availability_status
    if destination_area is not _UNSET:
        if destination_area is None:
            profile.destination_area = None
            profile.destination_expires_at = None
        else:
            if not destination_area.is_active:
                raise BusinessRuleError('Selected area is not available.')
            ttl = destination_ttl_minutes or settings.DRIVER_DESTINATION_TTL_MINUTES
            profile.destination_area = destination_area
            profile.destination_expires_at = timezone.now() + timedelta(minutes=ttl)
    elif destination_ttl_minutes is not None:
        raise BusinessRuleError('destination_ttl_minutes requires destination_area.')
    profile.save()
    return profile


@transaction.atomic
def update_driver_location(user, *, latitude, longitude, current_area=None):
    """Store the driver's position and stamp its freshness. The area defaults to the nearest known one."""
    from apps.areas.models import Area

    profile = DriverProfile.objects.select_for_update().get_or_create(user=user)[0]
    if current_area is None:
        radius = settings.DRIVER_MATCH_RADIUS_KM
        nearest, best = None, radius
        for area in Area.objects.filter(is_active=True, latitude__isnull=False, longitude__isnull=False):
            distance = haversine_km(float(latitude), float(longitude), float(area.latitude), float(area.longitude))
            if distance <= best:
                nearest, best = area, distance
        current_area = nearest
    profile.current_latitude = latitude
    profile.current_longitude = longitude
    profile.current_area = current_area
    profile.location_updated_at = timezone.now()
    profile.save()
    return profile

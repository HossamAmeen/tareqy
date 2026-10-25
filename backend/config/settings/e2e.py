"""Settings for the Playwright browser tests (frontend/e2e). Never use outside a throwaway database."""

from .development import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, 'e2e_support']  # noqa: F405
ROOT_URLCONF = 'e2e_support.urls'

# OTP codes stay in process memory and are read by the tests through /e2e/otp/.
SMS_BACKEND = 'apps.accounts.sms.LocMemSMSBackend'
OTP_RESEND_COOLDOWN_SECONDS = 0
CELERY_TASK_ALWAYS_EAGER = True
# Drivers still need admin verification: the tests exercise that flow.
DRIVER_VERIFICATION_REQUIRED = True

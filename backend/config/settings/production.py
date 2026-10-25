from .base import *

DEBUG = False

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_HTTPONLY = True

# Fail fast on unsafe production configuration instead of running half-secure.
from django.core.exceptions import ImproperlyConfigured  # noqa: E402

if len(SECRET_KEY) < 32:
    raise ImproperlyConfigured('SECRET_KEY must be at least 32 characters in production.')
if SMS_BACKEND.endswith('ConsoleSMSBackend'):
    raise ImproperlyConfigured('The console SMS backend logs verification codes; configure a real SMS backend.')
if any('localhost' in origin or '127.0.0.1' in origin for origin in CORS_ALLOWED_ORIGINS):
    raise ImproperlyConfigured('CORS_ALLOWED_ORIGINS must list only the production frontend origin(s).')

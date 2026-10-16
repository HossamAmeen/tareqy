from datetime import timedelta
from pathlib import Path

import dj_database_url
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'apps.health',
    'apps.areas',
    'apps.accounts',
    'apps.trips',
    'apps.matching',
    'apps.notifications',
    'apps.reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database: SQLite locally, PostgreSQL in staging/production via DATABASE_URL.
DATABASES = {
    'default': dj_database_url.config(
        env='DATABASE_URL',
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ar'
TIME_ZONE = env('TIME_ZONE', default='Africa/Cairo')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = env('STATIC_PATH', default=str(BASE_DIR / 'static'))
MEDIA_URL = 'media/'
MEDIA_ROOT = env('MEDIA_PATH', default=str(BASE_DIR / 'media'))
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:5173'])

# Rate limiting (shared cache required when running multiple instances)
RATELIMIT_CACHE_URL = env('RATELIMIT_CACHE_URL', default='')
if RATELIMIT_CACHE_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': RATELIMIT_CACHE_URL,
        }
    }
else:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'common.exception_handler.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': env('RATELIMIT_ANON', default='60/minute'),
        'user': env('RATELIMIT_USER', default='300/minute'),
        'auth': env('RATELIMIT_AUTH', default='10/minute'),
        'sensitive': env('RATELIMIT_SENSITIVE', default='30/minute'),
        'health': env('RATELIMIT_HEALTH', default='120/minute'),
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=30)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7)),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Fi Tariqi API',
    'DESCRIPTION': 'Ride-matching API (MVP).',
    'VERSION': '0.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

JAZZMIN_SETTINGS = {
    'site_title': 'Fi Tariqi Admin',
    'site_header': 'Fi Tariqi',
    'site_brand': 'Fi Tariqi',
    'welcome_sign': 'Welcome to the administration panel',
    'copyright': 'Fi Tariqi',
    'show_sidebar': True,
    'navigation_expanded': True,
}

HEALTH_CHECK_PASSWORD = env('HEALTH_CHECK_PASSWORD', default='')

# Celery (optional infrastructure)
CELERY_ENABLED = env.bool('CELERY_ENABLED', default=False)
CELERY_BEAT_ENABLED = env.bool('CELERY_BEAT_ENABLED', default=False)
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')
# Without Celery, tasks run inline so no broker is needed.
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=False) or not CELERY_ENABLED
CELERY_TASK_EAGER_PROPAGATES = env.bool('CELERY_TASK_EAGER_PROPAGATES', default=False)
CELERY_WORKER_CONCURRENCY = env.int('CELERY_WORKER_CONCURRENCY', default=2)

# Business settings (business doc sections 6-7)
REQUEST_TTL_MINUTES = env.int('REQUEST_TTL_MINUTES', default=30)
DRIVER_LOCATION_STALE_SECONDS = env.int('DRIVER_LOCATION_STALE_SECONDS', default=120)
AUTH_USER_MODEL = 'accounts.User'

# OTP login
OTP_LENGTH = env.int('OTP_LENGTH', default=6)
OTP_TTL_SECONDS = env.int('OTP_TTL_SECONDS', default=300)
OTP_MAX_ATTEMPTS = env.int('OTP_MAX_ATTEMPTS', default=5)
OTP_RESEND_COOLDOWN_SECONDS = env.int('OTP_RESEND_COOLDOWN_SECONDS', default=60)
# Dotted path of the SMS sender. The console backend only logs, never use it in production.
SMS_BACKEND = env('SMS_BACKEND', default='apps.accounts.sms.ConsoleSMSBackend')

if CELERY_BEAT_ENABLED:
    CELERY_BEAT_SCHEDULE = {
        'expire-trip-requests': {'task': 'apps.trips.tasks.expire_requests', 'schedule': 60.0},
    }

import hmac

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.responses import error_response, success_response
from common.throttling import HealthRateThrottle


def _password_is_valid(request):
    configured = settings.HEALTH_CHECK_PASSWORD
    provided = request.headers.get('X-Health-Check-Token') or request.query_params.get('password', '')
    if not configured or not provided:
        return False
    return hmac.compare_digest(provided.encode(), configured.encode())


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [HealthRateThrottle]

    @extend_schema(responses={200: None, 403: None, 429: None}, auth=[])
    def get(self, request):
        if not _password_is_valid(request):
            return error_response('Invalid health check password.', status_code=403)
        return success_response({'status': 'healthy'}, message='Service is healthy.')


class ReadinessView(APIView):
    """Checks the database; checks Celery/Redis only when enabled."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [HealthRateThrottle]

    @extend_schema(responses={200: None, 403: None, 503: None, 429: None}, auth=[])
    def get(self, request):
        if not _password_is_valid(request):
            return error_response('Invalid health check password.', status_code=403)

        from django.db import connection

        checks = {}
        try:
            connection.ensure_connection()
            checks['database'] = 'ok'
        except Exception:
            checks['database'] = 'unavailable'

        if settings.CELERY_ENABLED:
            try:
                import redis

                redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2).ping()
                checks['broker'] = 'ok'
            except Exception:
                checks['broker'] = 'unavailable'

        if 'unavailable' in checks.values():
            return error_response('Service is not ready.', checks, status_code=503)
        return success_response(checks, message='Service is ready.')

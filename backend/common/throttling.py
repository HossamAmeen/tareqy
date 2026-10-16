from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """Stricter limit for token/OTP endpoints (keyed by IP; callers are unauthenticated)."""

    scope = 'auth'


class SensitiveRateThrottle(UserRateThrottle):
    scope = 'sensitive'


class HealthRateThrottle(AnonRateThrottle):
    scope = 'health'

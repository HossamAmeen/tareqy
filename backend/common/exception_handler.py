import logging

from rest_framework import exceptions, status
from rest_framework.views import exception_handler

from .responses import error_response

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Format every API error as {success, message, errors}."""
    response = exception_handler(exc, context)

    if response is None:
        logger.exception('Unhandled API exception', exc_info=exc)
        return error_response('Internal server error.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if isinstance(exc, exceptions.ValidationError):
        message, errors = 'Validation failed.', response.data
    elif isinstance(exc, exceptions.Throttled):
        message, errors = 'Request rate limit exceeded.', {}
    else:
        message, errors = str(getattr(exc, 'detail', 'Request failed.')), {}

    formatted = error_response(message, errors, response.status_code)
    for header, value in response.items():  # keep Retry-After, WWW-Authenticate...
        formatted[header] = value
    return formatted

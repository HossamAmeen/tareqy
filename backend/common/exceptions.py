from rest_framework import status
from rest_framework.exceptions import APIException


class BusinessRuleError(APIException):
    """Raised by services when a business rule is violated."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Business rule violated.'
    default_code = 'business_rule_violation'


class ConflictError(BusinessRuleError):
    """State conflict, e.g. request already confirmed by another driver."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = 'The resource is in a conflicting state.'
    default_code = 'conflict'

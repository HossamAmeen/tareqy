from rest_framework import status
from rest_framework.response import Response


def success_response(
    data=None,
    message='Operation completed successfully.',
    status_code=status.HTTP_200_OK,
):
    return Response(
        {'success': True, 'message': message, 'data': {} if data is None else data},
        status=status_code,
    )


def error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {'success': False, 'message': message, 'errors': errors or {}},
        status=status_code,
    )

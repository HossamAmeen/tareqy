from rest_framework.response import Response


class EnvelopeMixin:
    """Wrap successful responses of generic views/viewsets in the standard {success, message, data} format."""

    def finalize_response(self, request, response, *args, **kwargs):
        if (
            isinstance(response, Response)
            and response.status_code < 400
            and response.data is not None
            and not (isinstance(response.data, dict) and 'success' in response.data)
        ):
            response.data = {'success': True, 'message': '', 'data': response.data}
        return super().finalize_response(request, response, *args, **kwargs)

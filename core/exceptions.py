
import logging

from rest_framework.views import exception_handler

security_logger = logging.getLogger("django.security")
logger = logging.getLogger("core")


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    request = context.get("request")

    if response is not None:
        status_code = response.status_code

        if status_code in (401, 403):
            user = getattr(request, "user", None)

            user_id = (
                user.pk
                if user and user.is_authenticated
                else None
            )

            security_logger.warning(
                "Access denied: status=%s method=%s path=%s user_id=%s",
                status_code,
                getattr(request, "method", "unknown"),
                getattr(request, "path", "unknown"),
                user_id,
            )

        response.data = {
            "success": False,
            "status_code": status_code,
            "error": response.data,
        }

    else:
        logger.exception(
            "Unhandled exception in API request",
            exc_info=(type(exc), exc, exc.__traceback__),
        )

    return response

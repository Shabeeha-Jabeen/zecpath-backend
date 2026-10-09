from django.http import JsonResponse


def custom_404(request, exception):
    return JsonResponse(
        {
            "success": False,
            "status_code": 404,
            "error": {
                "detail": "The requested resource was not found."
            }
        },
        status=404
    )


def custom_500(request):
    return JsonResponse(
        {
            "success": False,
            "status_code": 500,
            "error": {
                "detail": "Internal server error."
            }
        },
        status=500
    )
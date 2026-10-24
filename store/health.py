from django.http import JsonResponse


def healthcheck(request):
    """Lightweight process health endpoint for hosting-platform checks."""
    return JsonResponse({"status": "ok"})

from django.http import HttpResponse


def robots_txt(request):
    """Serve a minimal robots policy from the Django origin."""
    return HttpResponse(
        "User-agent: *\nAllow: /\n",
        content_type="text/plain; charset=utf-8",
    )

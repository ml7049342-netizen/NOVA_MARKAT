from django.http import HttpResponse


def robots_txt(request):
    """Serve a minimal robots policy from the Django origin."""
    return HttpResponse(
        "User-agent: *\nAllow: /\n",
        content_type="text/plain; charset=utf-8",
    )


def service_worker(request):
    """Serve a minimal same-origin worker for clients that still request /sw.js."""
    return HttpResponse(
        "self.addEventListener('install', () => self.skipWaiting());\n"
        "self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));\n",
        content_type="application/javascript; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )

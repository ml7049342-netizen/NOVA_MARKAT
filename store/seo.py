from django.contrib.staticfiles.storage import staticfiles_storage
from django.http import HttpResponse, HttpResponsePermanentRedirect, JsonResponse


def favicon(request):
    """Redirect to the manifest-hashed logo path produced by collectstatic."""
    return HttpResponsePermanentRedirect(staticfiles_storage.url("logo.svg"))


def web_manifest(request):
    """Serve a PWA manifest whose icon URL matches the active static-file manifest."""
    return JsonResponse(
        {
            "id": "/",
            "name": "NOVA MARKAT",
            "short_name": "NOVA",
            "description": "سوق إلكتروني جزائري يجمع المشترين والبائعين والموردين وشركات التوصيل.",
            "lang": "ar",
            "dir": "rtl",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#080d15",
            "theme_color": "#080d15",
            "icons": [
                {
                    "src": staticfiles_storage.url("logo.svg"),
                    "sizes": "any",
                    "type": "image/svg+xml",
                    "purpose": "any",
                }
            ],
        },
        headers={"Cache-Control": "no-cache"},
    )


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

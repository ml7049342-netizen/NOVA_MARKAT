import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, Http404
from django.utils._os import safe_join
from django.views.decorators.http import require_GET


ALLOWED_MEDIA_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@require_GET
def serve_media(request, path):
    """Serve uploaded image files from MEDIA_ROOT, including in production.

    Persistent storage must be mounted at MEDIA_ROOT on the hosting service.
    Only image formats accepted by the upload forms are exposed.
    """
    try:
        full_path = Path(safe_join(str(settings.MEDIA_ROOT), path))
    except (SuspiciousFileOperation, ValueError):
        raise Http404("Media file not found")

    if full_path.suffix.lower() not in ALLOWED_MEDIA_SUFFIXES or not full_path.is_file():
        raise Http404("Media file not found")

    content_type, _encoding = mimetypes.guess_type(full_path.name)
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise Http404("Media file not found")

    response = FileResponse(full_path.open("rb"), content_type=content_type)
    response["Cache-Control"] = "public, max-age=3600"
    response["X-Content-Type-Options"] = "nosniff"
    return response

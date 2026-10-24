import tempfile
from pathlib import Path

from django.test import Client, SimpleTestCase, override_settings


class UploadedMediaServingTests(SimpleTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.media_root = Path(self.tempdir.name)
        self.avatar_dir = self.media_root / "avatars"
        self.avatar_dir.mkdir()

    def test_uploaded_image_is_served_when_debug_is_off(self):
        image_path = self.avatar_dir / "avatar.png"
        image_path.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        )
        with override_settings(DEBUG=False, MEDIA_ROOT=self.media_root):
            response = Client().get("/media/avatars/avatar.png")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(b"".join(response.streaming_content)[:8], b"\x89PNG\r\n\x1a\n")

    def test_non_image_uploads_are_not_served(self):
        (self.avatar_dir / "payload.html").write_text("<script>alert(1)</script>")
        with override_settings(DEBUG=False, MEDIA_ROOT=self.media_root):
            response = Client().get("/media/avatars/payload.html")

        self.assertEqual(response.status_code, 404)

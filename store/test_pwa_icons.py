from django.test import TestCase
from django.urls import reverse


class PwaIconTests(TestCase):
    def test_manifest_contains_chromium_required_png_icon_sizes(self):
        response = self.client.get(reverse("manifest"))
        self.assertEqual(response.status_code, 200)

        icons = {
            icon.get("sizes"): icon
            for icon in response.json()["icons"]
            if icon.get("type") == "image/png"
        }
        for size, filename in (
            ("192x192", "logo-192"),
            ("512x512", "logo-512"),
        ):
            with self.subTest(size=size):
                icon = icons[size]
                self.assertEqual(icon["purpose"], "any")
                self.assertRegex(
                    icon["src"],
                    rf"^/static/{filename}\.[a-f0-9]+\.png$",
                )

    def test_homepage_exposes_apple_touch_icon(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertRegex(
            response.content.decode(),
            r'rel="apple-touch-icon" href="/static/logo-192\.[a-f0-9]+\.png"',
        )

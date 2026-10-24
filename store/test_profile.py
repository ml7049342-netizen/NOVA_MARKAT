from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile-user",
            email="old@example.com",
            password="A-strong-test-password-123",
            role="buyer",
        )

    def test_profile_requires_authentication(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_user_can_update_own_profile_fields(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("profile"), {
            "username": "updated-user",
            "email": "NEW@example.com",
            "phone": "0550123456",
        })
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "updated-user")
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(self.user.phone, "0550123456")

    def test_user_cannot_change_role_through_profile_form(self):
        self.client.force_login(self.user)
        self.client.post(reverse("profile"), {
            "username": self.user.username,
            "email": self.user.email,
            "phone": "0550123456",
            "role": "admin",
            "is_superuser": "on",
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, "buyer")
        self.assertFalse(self.user.is_superuser)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(
            username="other-user",
            email="taken@example.com",
            password="A-strong-test-password-123",
        )
        self.client.force_login(self.user)
        response = self.client.post(reverse("profile"), {
            "username": self.user.username,
            "email": "TAKEN@example.com",
            "phone": "0550123456",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هذا البريد الإلكتروني مستخدم بالفعل.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")

    def test_invalid_avatar_file_is_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_login(self.user)
        response = self.client.post(reverse("profile"), {
            "username": self.user.username,
            "email": self.user.email,
            "phone": "0550123456",
            "avatar": SimpleUploadedFile(
                "avatar.png", b"this is not a real image", content_type="image/png"
            ),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "قم برفع صورة صحيحة")
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)

    def test_avatar_larger_than_two_megabytes_is_rejected(self):
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buffer = BytesIO()
        Image.effect_noise((1400, 1400), 100).convert("RGB").save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        self.assertGreater(len(image_bytes), 2 * 1024 * 1024)

        self.client.force_login(self.user)
        response = self.client.post(reverse("profile"), {
            "username": self.user.username,
            "email": self.user.email,
            "phone": "0550123456",
            "avatar": SimpleUploadedFile(
                "large.png", image_bytes, content_type="image/png"
            ),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "حجم الصورة يجب ألا يتجاوز 2 ميغابايت.")
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)

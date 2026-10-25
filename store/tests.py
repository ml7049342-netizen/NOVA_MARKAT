from django.test import TestCase
from django.urls import reverse
from store.forms import RegisterForm
from store.models import User


class HomePageTests(TestCase):
    def test_homepage_loads_without_catalog_items(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NOVA MARKAT")


class RegistrationFormTests(TestCase):
    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(
            username="existing-user",
            email="customer@example.com",
            password="Strong-test-password-983!",
        )
        form = RegisterForm(data={
            "username": "new-user",
            "email": " CUSTOMER@example.com ",
            "phone": "0551234567",
            "role": "buyer",
            "password1": "Another-strong-password-731!",
            "password2": "Another-strong-password-731!",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class CommercialAccountApprovalTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="pending-seller",
            email="seller@example.com",
            password="Strong-test-password-983!",
            role="seller",
            is_verified=False,
        )
        self.client.force_login(self.seller)

    def test_unapproved_seller_dashboard_redirects_to_pending_page(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("approval_pending"))

    def test_unapproved_seller_cannot_open_product_creation(self):
        response = self.client.get(reverse("seller_product_add"))
        self.assertRedirects(response, reverse("approval_pending"))

    def test_pending_approval_page_loads(self):
        response = self.client.get(reverse("approval_pending"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "قيد المراجعة")

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from store.models import Category, Product


User = get_user_model()


class PublicPageTests(TestCase):
    def test_homepage_returns_ok(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_delivery_directory_returns_ok(self):
        response = self.client.get(reverse("delivery_companies"))
        self.assertEqual(response.status_code, 200)

    def test_favicon_redirects_to_static_logo(self):
        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/static/logo.svg")


class CartTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="test-seller",
            password="SafeTestPassword-2026!",
            role="seller",
            is_verified=True,
        )
        self.category = Category.objects.create(name="اختبار")
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="منتج تجريبي",
            description="منتج للاختبار الآلي فقط",
            price="1250.00",
            stock=3,
            active=True,
        )

    def test_add_to_cart_requires_post(self):
        response = self.client.get(
            reverse("add_to_cart", args=[self.product.pk]),
        )
        self.assertEqual(response.status_code, 405)

    def test_add_to_cart_updates_session_without_creating_order(self):
        response = self.client.post(
            reverse("add_to_cart", args=[self.product.pk]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["cart"], {str(self.product.pk): 1})
        self.assertEqual(self.product.stock, 3)

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
import json

from store.models import Category, Product, Order

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

    def test_robots_txt_is_served(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn("User-agent: *", response.content.decode())


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
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(Order.objects.count(), 0)

    def test_fake_api_product_request_returns_product(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("products", payload)
        self.assertTrue(any(p["id"] == self.product.pk for p in payload["products"]))

    def test_fake_api_cart_request_adds_only_to_test_session(self):
        response = self.client.post(
            f"/api/cart/add/{self.product.pk}/",
            data=json.dumps({"quantity": 2}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["quantity"], 2)
        self.assertEqual(self.client.session["cart"], {str(self.product.pk): 2})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(Order.objects.count(), 0)

    def test_fake_api_cart_rejects_quantity_above_stock(self):
        response = self.client.post(
            f"/api/cart/add/{self.product.pk}/",
            data=json.dumps({"quantity": 4}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.session.get("cart", {}), {})
        self.assertEqual(Order.objects.count(), 0)

    def test_fake_api_cart_rejects_invalid_quantity(self):
        response = self.client.post(
            f"/api/cart/add/{self.product.pk}/",
            data=json.dumps({"quantity": -1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.session.get("cart", {}), {})
        self.assertEqual(Order.objects.count(), 0)

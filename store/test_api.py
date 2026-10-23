import json

from django.test import TestCase
from django.urls import reverse

from .models import Category, Product, User


class StorefrontApiTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="seller-test",
            password="SafeTestPass123!",
            role="seller",
        )
        self.category = Category.objects.create(name="اختبار", active=True)
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="منتج اختبار",
            description="منتج لاختبار واجهة المتجر",
            price="1250.00",
            stock=5,
            active=True,
        )

    def test_catalog_returns_only_available_real_products(self):
        response = self.client.get(reverse("api_products"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["products"]), 1)
        self.assertEqual(payload["products"][0]["id"], self.product.pk)
        self.assertEqual(payload["products"][0]["price"], "1250.00")

    def test_catalog_hides_out_of_stock_products(self):
        self.product.stock = 0
        self.product.save(update_fields=["stock"])
        response = self.client.get(reverse("api_products"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["products"], [])

    def test_cart_add_requires_post_and_persists_in_session(self):
        response = self.client.post(
            reverse("api_cart_add", args=[self.product.pk]),
            data=json.dumps({"quantity": 2}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["quantity"], 2)
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 2)

    def test_cart_rejects_quantity_above_stock(self):
        response = self.client.post(
            reverse("api_cart_add", args=[self.product.pk]),
            data=json.dumps({"quantity": 6}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(str(self.product.pk), self.client.session.get("cart", {}))

    def test_cart_set_rejects_unknown_products(self):
        response = self.client.post(
            reverse("api_cart_set"),
            data=json.dumps({"items": {"999999": 1}}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_csrf_endpoint_returns_token(self):
        response = self.client.get(reverse("api_csrf"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("csrfToken"))

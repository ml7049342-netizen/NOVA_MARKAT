import json

from django.test import Client, TestCase
from django.urls import reverse

from .models import Category, DeliveryCompany, Order, Product, User


class StorefrontApiTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="seller-test", password="SafeTestPass123!", role="seller"
        )
        self.buyer = User.objects.create_user(
            username="buyer-test", password="SafeTestPass123!", role="buyer"
        )
        self.category = Category.objects.create(name="اختبار", active=True)
        self.product = Product.objects.create(
            seller=self.seller, category=self.category, name="منتج اختبار",
            description="منتج لاختبار واجهة المتجر", price="1250.00",
            stock=5, active=True,
        )

    def post_json(self, url, payload, client=None):
        return (client or self.client).post(
            url, data=json.dumps(payload), content_type="application/json"
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

    def test_delivery_catalog_only_returns_verified_companies(self):
        DeliveryCompany.objects.create(
            owner=self.seller, name="موثقة", verified=True, wilayas=["31"]
        )
        DeliveryCompany.objects.create(
            owner=self.buyer, name="غير موثقة", verified=False, wilayas=["31"]
        )
        response = self.client.get(reverse("api_delivery_companies"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c["name"] for c in response.json()["companies"]], ["موثقة"])

    def test_cart_add_requires_post_and_persists_in_session(self):
        response = self.post_json(reverse("api_cart_add", args=[self.product.pk]), {"quantity": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["quantity"], 2)
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 2)

    def test_cart_rejects_quantity_above_stock(self):
        response = self.post_json(reverse("api_cart_add", args=[self.product.pk]), {"quantity": 6})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(str(self.product.pk), self.client.session.get("cart", {}))

    def test_cart_rejects_malformed_json_and_boolean_quantity(self):
        malformed = self.client.post(
            reverse("api_cart_add", args=[self.product.pk]), data="{broken",
            content_type="application/json",
        )
        boolean_quantity = self.post_json(
            reverse("api_cart_add", args=[self.product.pk]), {"quantity": True}
        )
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(boolean_quantity.status_code, 400)

    def test_cart_set_rejects_unknown_products(self):
        response = self.post_json(reverse("api_cart_set"), {"items": {"999999": 1}})
        self.assertEqual(response.status_code, 400)

    def test_cart_set_rejects_noncanonical_and_duplicate_product_ids(self):
        for items in ({"01": 1}, {"1": 1, "01": 2}):
            with self.subTest(items=items):
                response = self.post_json(reverse("api_cart_set"), {"items": items})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.client.session.get("cart", {}), {})

    def test_cart_get_restores_server_session_cart(self):
        session = self.client.session
        session["cart"] = {str(self.product.pk): 2, "999999": 1}
        session.save()
        response = self.client.get(reverse("api_cart_set"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], {str(self.product.pk): 2})
        self.assertEqual(response.json()["cartCount"], 2)

    def test_csrf_endpoint_returns_token(self):
        response = self.client.get(reverse("api_csrf"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("csrfToken"))

    def test_csrf_protects_cart_mutations(self):
        strict_client = Client(enforce_csrf_checks=True)
        response = self.post_json(
            reverse("api_cart_add", args=[self.product.pk]), {"quantity": 1},
            client=strict_client,
        )
        self.assertEqual(response.status_code, 403)

    def test_csrf_token_allows_cart_mutation(self):
        strict_client = Client(enforce_csrf_checks=True)
        token_response = strict_client.get(reverse("api_csrf"))
        self.assertEqual(token_response.status_code, 200)
        token = token_response.json()["csrfToken"]
        response = strict_client.post(
            reverse("api_cart_add", args=[self.product.pk]),
            data=json.dumps({"quantity": 1}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["quantity"], 1)

    def test_checkout_rejects_missing_product_without_creating_order(self):
        self.client.force_login(self.buyer)
        session = self.client.session
        session["cart"] = {str(self.product.pk): 1, "999999": 1}
        session.save()
        self.client.post(
            reverse("checkout"),
            {"wilaya": "31", "address": "عنوان اختبار", "phone": "0550000000"},
        )
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_checkout_rejects_quantity_above_stock_without_order(self):
        self.client.force_login(self.buyer)
        session = self.client.session
        session["cart"] = {str(self.product.pk): 6}
        session.save()
        self.client.post(
            reverse("checkout"),
            {"wilaya": "31", "address": "عنوان اختبار", "phone": "0550000000"},
        )
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_checkout_creates_order_and_decrements_stock(self):
        self.client.force_login(self.buyer)
        session = self.client.session
        session["cart"] = {str(self.product.pk): 2}
        session.save()
        response = self.client.post(
            reverse("checkout"),
            {"wilaya": "31", "address": "عنوان اختبار", "phone": "0550000000"},
        )
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get()
        self.assertEqual(order.buyer, self.buyer)
        self.assertEqual(str(order.total), "2500.00")
        self.assertEqual(order.items.get().quantity, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.client.session["cart"], {})

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
        self.assertContains(response, 'rel="manifest"')
        self.assertContains(response, 'navigator.serviceWorker.register("/sw.js")')

    def test_delivery_directory_returns_ok(self):
        response = self.client.get(reverse("delivery_companies"))
        self.assertEqual(response.status_code, 200)

    def test_favicon_redirects_to_hashed_static_logo(self):
        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 301)
        self.assertRegex(response["Location"], r"^/static/logo\\.[a-f0-9]+\\.svg$")

    def test_manifest_uses_the_hashed_static_logo_url(self):
        response = self.client.get(reverse("manifest"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-cache")
        manifest = response.json()
        self.assertEqual(manifest["lang"], "ar")
        self.assertEqual(manifest["dir"], "rtl")
        self.assertRegex(manifest["icons"][0]["src"], r"^/static/logo\\.[a-f0-9]+\\.svg$")

    def test_robots_txt_is_served(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn("User-agent: *", response.content.decode())

    def test_service_worker_is_served_without_cache(self):
        response = self.client.get("/sw.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/javascript", response["Content-Type"])
        self.assertEqual(response["Cache-Control"], "no-cache")
        self.assertIn("skipWaiting", response.content.decode())


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


    def test_add_to_cart_repairs_negative_session_quantity(self):
        session = self.client.session
        session["cart"] = {str(self.product.pk): -4}
        session.save()

        response = self.client.post(reverse("add_to_cart", args=[self.product.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["cart"], {str(self.product.pk): 1})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(Order.objects.count(), 0)

    def test_add_to_cart_clamps_stale_quantity_to_current_stock(self):
        session = self.client.session
        session["cart"] = {str(self.product.pk): 99}
        session.save()

        response = self.client.post(reverse("add_to_cart", args=[self.product.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["cart"], {str(self.product.pk): 3})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(Order.objects.count(), 0)


    def test_fake_api_cart_rejects_fractional_and_boolean_quantities(self):
        for quantity in (2.5, True):
            with self.subTest(quantity=quantity):
                response = self.client.post(
                    f"/api/cart/add/{self.product.pk}/",
                    data=json.dumps({"quantity": quantity}),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.client.session.get("cart", {}), {})
                self.assertEqual(Order.objects.count(), 0)


class FakeCheckoutTests(TestCase):
    """End-to-end checkout tests using only Django's temporary test database."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username="checkout-test-seller",
            password="SafeTestPassword-2026!",
            role="seller",
            is_verified=True,
        )
        self.category = Category.objects.create(name="اختبار شراء")
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="منتج شراء تجريبي",
            description="منتج وهمي لاختبار إتمام الطلب",
            price="1250.00",
            stock=3,
            active=True,
        )
        self.buyer = User.objects.create_user(
            username="test-buyer",
            password="SafeTestPassword-2026!",
            role="buyer",
        )
        self.client.force_login(self.buyer)
        session = self.client.session
        session["cart"] = {str(self.product.pk): 2}
        session.save()

    def test_fake_checkout_persists_order_and_items_and_updates_stock(self):
        response = self.client.post(
            reverse("checkout"),
            {
                "wilaya": "16",
                "address": "عنوان اختبار غير حقيقي",
                "phone": "0555123456",
            },
        )
        self.assertRedirects(response, reverse("orders"), fetch_redirect_response=False)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()
        self.assertEqual(order.buyer, self.buyer)
        self.assertEqual(order.wilaya, "16")
        self.assertEqual(order.phone, "0555123456")
        self.assertEqual(str(order.total), "2500.00")
        self.assertEqual(order.items.count(), 1)
        item = order.items.get()
        self.assertEqual(item.product_id, self.product.pk)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(str(item.unit_price), "1250.00")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertEqual(self.client.session.get("cart"), {})

    def test_fake_checkout_rejects_invalid_phone_without_order_or_stock_change(self):
        response = self.client.post(
            reverse("checkout"),
            {
                "wilaya": "16",
                "address": "عنوان اختبار غير حقيقي",
                "phone": "123",
            },
        )
        self.assertRedirects(response, reverse("checkout"), fetch_redirect_response=False)
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_fake_checkout_rejects_quantity_above_stock_without_order(self):
        session = self.client.session
        session["cart"] = {str(self.product.pk): 4}
        session.save()
        response = self.client.post(
            reverse("checkout"),
            {
                "wilaya": "16",
                "address": "عنوان اختبار غير حقيقي",
                "phone": "0555123456",
            },
        )
        self.assertRedirects(response, reverse("cart"), fetch_redirect_response=False)
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)


    def test_fake_checkout_rejects_boolean_quantity_without_order_or_stock_change(self):
        session = self.client.session
        session["cart"] = {str(self.product.pk): True}
        session.save()
        response = self.client.post(
            reverse("checkout"),
            {
                "wilaya": "16",
                "address": "عنوان اختبار غير حقيقي",
                "phone": "0555123456",
            },
        )
        self.assertRedirects(response, reverse("cart"), fetch_redirect_response=False)
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_fake_checkout_rejects_invalid_wilaya_without_order_or_stock_change(self):
        response = self.client.post(
            reverse("checkout"),
            {
                "wilaya": "999",
                "address": "عنوان اختبار غير حقيقي",
                "phone": "0555123456",
            },
        )
        self.assertRedirects(response, reverse("checkout"), fetch_redirect_response=False)
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_fake_checkout_rejects_empty_address_without_order_or_stock_change(self):
        response = self.client.post(
            reverse("checkout"),
            {
                "wilaya": "16",
                "address": "   ",
                "phone": "0555123456",
            },
        )
        self.assertRedirects(response, reverse("checkout"), fetch_redirect_response=False)
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_fake_checkout_rejects_oversized_cart_without_order_or_stock_change(self):
        session = self.client.session
        session["cart"] = {str(index): 1 for index in range(1, 52)}
        session.save()

        response = self.client.post(
            reverse("checkout"),
            {
                "wilaya": "16",
                "address": "عنوان اختبار غير حقيقي",
                "phone": "0555123456",
            },
        )

        self.assertRedirects(response, reverse("cart"), fetch_redirect_response=False)
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_fake_checkout_rejects_duplicate_normalized_product_ids(self):
        session = self.client.session
        session["cart"] = {str(self.product.pk): 1, f"0{self.product.pk}": 1}
        session.save()

        response = self.client.post(
            reverse("checkout"),
            {
                "wilaya": "16",
                "address": "عنوان اختبار غير حقيقي",
                "phone": "0555123456",
            },
        )

        self.assertRedirects(response, reverse("cart"), fetch_redirect_response=False)
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)


from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from store.models import Category, Order, Product, WILAYAS

User = get_user_model()


class WilayaValidationTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="wilaya-test-seller",
            password="SafeTestPassword-2026!",
            role="seller",
            is_verified=True,
        )
        self.buyer = User.objects.create_user(
            username="wilaya-test-buyer",
            password="SafeTestPassword-2026!",
            role="buyer",
        )
        category = Category.objects.create(name="اختبار الولايات")
        self.product = Product.objects.create(
            seller=self.seller,
            category=category,
            name="منتج وهمي لاختبار الولايات",
            description="بيانات اختبار فقط",
            price="100.00",
            stock=2,
            active=True,
        )
        self.client.force_login(self.buyer)
        session = self.client.session
        session["cart"] = {str(self.product.pk): 1}
        session.save()

    def test_wilaya_choices_cover_the_current_69_wilaya_division(self):
        self.assertEqual(len(WILAYAS), 69)
        self.assertEqual([value for value, _label in WILAYAS], [str(i) for i in range(1, 70)])

    def test_checkout_accepts_wilaya_69(self):
        response = self.client.post(
            reverse("checkout"),
            {
                "wilaya": "69",
                "address": "عنوان اختبار غير حقيقي",
                "phone": "0555123456",
            },
        )

        self.assertRedirects(response, reverse("orders"), fetch_redirect_response=False)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.get().wilaya, "69")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

    def test_checkout_rejects_wilaya_70_without_creating_order(self):
        response = self.client.post(
            reverse("checkout"),
            {
                "wilaya": "70",
                "address": "عنوان اختبار غير حقيقي",
                "phone": "0555123456",
            },
        )

        self.assertRedirects(response, reverse("checkout"), fetch_redirect_response=False)
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)

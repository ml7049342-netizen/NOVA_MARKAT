from decimal import Decimal, InvalidOperation
import json

from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import Product, DeliveryCompany


@ensure_csrf_cookie
@require_GET
def csrf_token(request):
    from django.middleware.csrf import get_token
    return JsonResponse({"csrfToken": get_token(request)})


@require_GET
def products(request):
    qs = Product.objects.filter(active=True, stock__gt=0).select_related("category", "seller").order_by("-created_at")[:100]
    items = []
    for p in qs:
        items.append({
            "id": p.pk,
            "name": p.name,
            "category": p.category.name if p.category else "عام",
            "description": p.description,
            "price": str(p.price),
            "stock": p.stock,
            "image": p.main_image.url if p.main_image else "",
            "seller": p.seller.username,
            "url": f"/products/{p.pk}/",
        })
    return JsonResponse({"products": items})


@require_GET
def delivery_companies(request):
    qs = DeliveryCompany.objects.filter(verified=True).order_by("-rating")[:100]
    return JsonResponse({"companies": [{
        "id": c.pk,
        "name": c.name,
        "description": c.description,
        "wilayas": c.wilayas,
        "rating": str(c.rating),
        "cash_on_delivery": c.cash_on_delivery,
    } for c in qs]})


@require_POST
def cart_add(request, pk):
    product = Product.objects.filter(pk=pk, active=True, stock__gt=0).first()
    if product is None:
        return JsonResponse({"error": "المنتج غير متاح حاليا."}, status=404)
    try:
        payload = json.loads(request.body or "{}")
        quantity = int(payload.get("quantity", 1))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"error": "الكمية غير صالحة."}, status=400)
    if quantity < 1 or quantity > product.stock or quantity > 99:
        return JsonResponse({"error": "الكمية تتجاوز المخزون المتاح."}, status=400)
    cart = request.session.get("cart", {})
    key = str(pk)
    next_quantity = int(cart.get(key, 0)) + quantity
    if next_quantity > product.stock:
        return JsonResponse({"error": "الكمية تتجاوز المخزون المتاح."}, status=400)
    cart[key] = next_quantity
    request.session["cart"] = cart
    return JsonResponse({"ok": True, "quantity": next_quantity, "cartCount": sum(int(v) for v in cart.values())})


@require_POST
def cart_set(request):
    try:
        payload = json.loads(request.body or "{}")
        requested = payload.get("items", {})
        if not isinstance(requested, dict):
            raise ValueError
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"error": "بيانات السلة غير صالحة."}, status=400)

    clean = {}
    for raw_id, raw_quantity in requested.items():
        try:
            product_id = int(raw_id)
            quantity = int(raw_quantity)
        except (ValueError, TypeError):
            return JsonResponse({"error": "بيانات منتج غير صالحة."}, status=400)
        if quantity <= 0:
            continue
        if quantity > 99:
            return JsonResponse({"error": "الكمية أكبر من الحد المسموح."}, status=400)
        product = Product.objects.filter(pk=product_id, active=True, stock__gt=0).first()
        if product is None or quantity > product.stock:
            return JsonResponse({"error": "أحد المنتجات لم يعد متاحًا بهذه الكمية."}, status=400)
        clean[str(product_id)] = quantity

    request.session["cart"] = clean
    return JsonResponse({"ok": True, "cartCount": sum(clean.values())})

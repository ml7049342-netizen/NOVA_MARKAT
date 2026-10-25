import json

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import DeliveryCompany, Product

MAX_CART_QUANTITY = 99
MAX_CART_ITEMS = 50


@ensure_csrf_cookie
@require_GET
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_GET
def products(request):
    qs = (
        Product.objects.filter(active=True, stock__gt=0)
        .select_related("category", "seller")
        .order_by("-created_at")[:100]
    )
    items = []
    for product in qs:
        items.append({
            "id": product.pk,
            "name": product.name,
            "category": product.category.name if product.category else "عام",
            "description": product.description,
            "price": str(product.price),
            "stock": product.stock,
            "image": product.main_image.url if product.main_image else "",
            "seller": product.seller.username,
            "url": f"/products/{product.pk}/",
        })
    return JsonResponse({"products": items})


@require_GET
def delivery_companies(request):
    companies = DeliveryCompany.objects.filter(verified=True).order_by("-rating")[:100]
    return JsonResponse({"companies": [{
        "id": company.pk,
        "name": company.name,
        "description": company.description,
        "wilayas": company.wilayas,
        "rating": str(company.rating),
        "cash_on_delivery": company.cash_on_delivery,
    } for company in companies]})


def _parse_json_body(request):
    try:
        payload = json.loads(request.body or "{}")
    except (ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def _strict_int(value):
    """Parse an integer without silently truncating floats or accepting booleans."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        try:
            return int(value)
        except (ValueError, OverflowError):
            return None
    return None


def _session_cart(request):
    raw_cart = request.session.get("cart", {})
    if not isinstance(raw_cart, dict):
        return {}
    clean = {}
    for raw_id, raw_quantity in raw_cart.items():
        product_id = _strict_int(raw_id)
        quantity = _strict_int(raw_quantity)
        if product_id is not None and quantity is not None and product_id > 0 and 1 <= quantity <= MAX_CART_QUANTITY:
            clean[str(product_id)] = quantity
    return clean


@require_POST
def cart_add(request, pk):
    product = Product.objects.filter(pk=pk, active=True, stock__gt=0).first()
    if product is None:
        return JsonResponse({"error": "المنتج غير متاح حاليا."}, status=404)
    payload = _parse_json_body(request)
    if payload is None:
        return JsonResponse({"error": "بيانات الطلب غير صالحة."}, status=400)
    raw_quantity = payload.get("quantity", 1)
    quantity = _strict_int(raw_quantity)
    if quantity is None:
        return JsonResponse({"error": "الكمية غير صالحة."}, status=400)
    if quantity < 1 or quantity > MAX_CART_QUANTITY:
        return JsonResponse({"error": "الكمية خارج الحد المسموح."}, status=400)
    cart = _session_cart(request)
    key = str(pk)
    next_quantity = cart.get(key, 0) + quantity
    if next_quantity > product.stock or next_quantity > MAX_CART_QUANTITY:
        return JsonResponse({"error": "الكمية تتجاوز المخزون المتاح."}, status=400)
    cart[key] = next_quantity
    if len(cart) > MAX_CART_ITEMS:
        return JsonResponse({"error": "عدد المنتجات في السلة تجاوز الحد المسموح."}, status=400)
    request.session["cart"] = cart
    return JsonResponse({"ok": True, "quantity": next_quantity, "cartCount": sum(cart.values())})


@require_http_methods(["GET", "POST"])
def cart_set(request):
    if request.method == "GET":
        cart = _session_cart(request)
        available = Product.objects.filter(
            pk__in=[int(product_id) for product_id in cart],
            active=True,
            stock__gt=0,
        )
        stock_by_id = {str(product.pk): product.stock for product in available}
        clean = {
            product_id: min(quantity, stock_by_id[product_id])
            for product_id, quantity in cart.items()
            if product_id in stock_by_id
        }
        request.session["cart"] = clean
        return JsonResponse({"items": clean, "cartCount": sum(clean.values())})

    payload = _parse_json_body(request)
    if payload is None:
        return JsonResponse({"error": "بيانات السلة غير صالحة."}, status=400)
    requested = payload.get("items", {})
    if not isinstance(requested, dict) or len(requested) > MAX_CART_ITEMS:
        return JsonResponse({"error": "بيانات السلة غير صالحة أو تحتوي منتجات كثيرة."}, status=400)
    clean = {}
    for raw_id, raw_quantity in requested.items():
        try:
            product_id = int(raw_id)
        except (ValueError, TypeError, OverflowError):
            return JsonResponse({"error": "معرّف المنتج غير صالح."}, status=400)
        if product_id <= 0 or isinstance(raw_quantity, bool):
            return JsonResponse({"error": "بيانات منتج غير صالحة."}, status=400)
        quantity = _strict_int(raw_quantity)
        if quantity is None:
            return JsonResponse({"error": "الكمية غير صالحة."}, status=400)
        if quantity == 0:
            continue
        if quantity < 0 or quantity > MAX_CART_QUANTITY:
            return JsonResponse({"error": "الكمية خارج الحد المسموح."}, status=400)
        product = Product.objects.filter(pk=product_id, active=True, stock__gt=0).first()
        if product is None or quantity > product.stock:
            return JsonResponse({"error": "أحد المنتجات لم يعد متاحًا بهذه الكمية."}, status=400)
        clean[str(product_id)] = quantity
    request.session["cart"] = clean
    return JsonResponse({"ok": True, "cartCount": sum(clean.values())})

from decimal import Decimal
import re
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from .forms import RegisterForm, ProductForm, SupplierProductForm, DeliveryCompanyForm
from .models import Product, DeliveryCompany, Notification, Order, OrderItem, DeliveryContractRequest, User, WILAYAS, Category, Review


def home(request):
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    products = Product.objects.filter(active=True, stock__gt=0).select_related("seller", "category")
    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(seller__username__icontains=q))
    if category:
        products = products.filter(category_id=category)
    return render(request, "home.html", {"products": products[:60], "categories": Category.objects.filter(active=True), "q": q})


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, active=True)
    if request.method == "POST" and request.user.is_authenticated:
        try:
            rating = int(request.POST.get("rating", 5))
        except (TypeError, ValueError):
            rating = 5
        rating = max(1, min(5, rating))
        comment = request.POST.get("comment", "").strip()[:2000]
        Review.objects.update_or_create(product=product, buyer=request.user, defaults={"rating": rating, "comment": comment})
        messages.success(request, "تم حفظ تقييمك.")
        return redirect("product_detail", pk=pk)
    return render(request, "product.html", {"product": product, "reviews": product.reviews.select_related("buyer")})


@require_POST
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk, active=True)
    cart = request.session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}
    key = str(pk)
    try:
        current = int(cart.get(key, 0))
    except (TypeError, ValueError):
        current = 0
    if product.stock < 1:
        messages.error(request, "هذا المنتج غير متوفر حاليًا.")
    elif current >= min(product.stock, 99):
        messages.error(request, "وصلت إلى الحد المتاح من هذا المنتج.")
    else:
        cart[key] = current + 1
        request.session["cart"] = cart
        messages.success(request, "تمت إضافة المنتج إلى السلة.")
    return redirect("cart")


def cart(request):
    data = request.session.get("cart", {})
    if not isinstance(data, dict):
        data = {}
    if request.method == "POST":
        valid_ids = set(Product.objects.filter(active=True).values_list("id", flat=True))
        for key, val in request.POST.items():
            if not key.startswith("qty_"):
                continue
            pid = key[4:]
            if not pid.isdigit() or int(pid) not in valid_ids:
                data.pop(pid, None)
                continue
            try:
                quantity = int(val)
            except (TypeError, ValueError):
                quantity = 0
            product = Product.objects.filter(pk=int(pid), active=True).first()
            quantity = max(0, min(quantity, product.stock, 99)) if product else 0
            if quantity:
                data[pid] = quantity
            else:
                data.pop(pid, None)
        request.session["cart"] = data
        return redirect("cart")

    products = Product.objects.filter(id__in=[key for key in data if str(key).isdigit()], active=True)
    rows = []
    total = Decimal("0")
    for product in products:
        try:
            quantity = int(data[str(product.id)])
        except (TypeError, ValueError, KeyError):
            continue
        if quantity < 1:
            continue
        subtotal = product.price * quantity
        total += subtotal
        rows.append((product, quantity, subtotal))
    return render(request, "cart.html", {"rows": rows, "total": total})


@login_required
@transaction.atomic
def checkout(request):
    data = request.session.get("cart", {})
    if not isinstance(data, dict) or not data:
        messages.error(request, "السلة فارغة.")
        return redirect("cart")

    if request.method == "POST":
        wilaya = request.POST.get("wilaya", "").strip()
        address = request.POST.get("address", "").strip()
        phone = request.POST.get("phone", "").strip()
        valid_wilayas = {value for value, _label in WILAYAS}
        if wilaya not in valid_wilayas:
            messages.error(request, "اختر ولاية صحيحة.")
            return redirect("checkout")
        if not address or len(address) > 500 or not phone or len(phone) > 30:
            messages.error(request, "تحقق من العنوان ورقم الهاتف.")
            return redirect("checkout")
        digits = re.sub(r"[\s().-]", "", phone)
        if not re.fullmatch(r"(?:\+213|00213|0)(?:5|6|7)\d{8}", digits):
            messages.error(request, "أدخل رقم هاتف جزائري صحيحًا.")
            return redirect("checkout")

        clean_cart = {}
        for key, value in data.items():
            if not str(key).isdigit():
                messages.error(request, "تحتوي السلة على عنصر غير صالح. حدّث السلة ثم أعد المحاولة.")
                return redirect("cart")
            try:
                quantity = int(value)
            except (TypeError, ValueError):
                quantity = 0
            if quantity < 1 or quantity > 99:
                messages.error(request, "توجد كمية غير صالحة في السلة.")
                return redirect("cart")
            clean_cart[str(int(key))] = quantity

        products = list(Product.objects.select_for_update().filter(id__in=clean_cart.keys(), active=True).select_related("seller"))
        if len(products) != len(clean_cart):
            messages.error(request, "تغيّر أحد المنتجات أو لم يعد متوفرًا. راجع السلة.")
            return redirect("cart")
        for product in products:
            if clean_cart[str(product.id)] > product.stock:
                messages.error(request, f"الكمية غير متوفرة: {product.name}")
                return redirect("cart")

        order = Order.objects.create(
            buyer=request.user, wilaya=wilaya, address=address, phone=digits,
            payment_method="cash_on_delivery",
        )
        total = Decimal("0")
        for product in products:
            quantity = clean_cart[str(product.id)]
            product.stock -= quantity
            product.save(update_fields=["stock"])
            OrderItem.objects.create(order=order, product=product, quantity=quantity, unit_price=product.price)
            total += product.price * quantity
            Notification.objects.create(user=product.seller, title="طلب جديد", body=f"لديك طلب جديد #{order.id}.")
        order.total = total
        order.save(update_fields=["total"])
        request.session["cart"] = {}
        Notification.objects.create(user=request.user, title="تم استلام طلبك", body=f"تم إنشاء الطلب #{order.id} والدفع عند الاستلام.")
        messages.success(request, f"تم إنشاء الطلب #{order.id}.")
        return redirect("orders")
    return render(request, "checkout.html", {"wilayas": WILAYAS})


@login_required
def orders(request):
    role = request.user.role
    base = Order.objects.prefetch_related("items__product").order_by("-created_at")
    if role in {"seller", "supplier", "delivery"} and not request.user.is_verified:
        orders_qs = base.filter(buyer=request.user)
    elif role == "seller":
        orders_qs = base.filter(items__product__seller=request.user).distinct()
    elif role == "delivery":
        company = getattr(request.user, "delivery_company", None)
        orders_qs = base.filter(delivery_company=company) if company else base.none()
    elif role == "supplier":
        orders_qs = base.none()
    elif role == "admin" or request.user.is_superuser:
        orders_qs = base
    else:
        orders_qs = base.filter(buyer=request.user)
    return render(request, "orders.html", {"orders": orders_qs})


@login_required
def dashboard(request):
    role = request.user.role
    if role in {"seller", "supplier", "delivery"} and not request.user.is_verified:
        messages.info(request, "تم إنشاء حسابك. هذا الدور بانتظار اعتماد الإدارة قبل تفعيل وظائفه.")
        return redirect("home")
    if role == "seller":
        products = request.user.products.select_related("category")
        items = OrderItem.objects.filter(product__seller=request.user)
        sales = sum((item.unit_price * item.quantity for item in items), Decimal("0"))
        return render(request, "dashboard_seller.html", {"products": products, "sales": sales, "orders_count": items.values("order_id").distinct().count()})
    if role == "supplier":
        return render(request, "dashboard_supplier.html", {"products": request.user.supplier_products.order_by("-id")})
    if role == "delivery":
        company = getattr(request.user, "delivery_company", None)
        requests = company.contract_requests.select_related("requester").order_by("-created_at") if company else []
        return render(request, "dashboard_delivery.html", {"company": company, "requests": requests})
    return render(request, "dashboard_buyer.html", {"orders": request.user.orders.order_by("-created_at")[:10]})


@login_required
def seller_product_add(request):
    if request.user.role != "seller":
        return redirect("dashboard")
    if not request.user.is_verified:
        messages.error(request, "حساب البائع بانتظار اعتماد الإدارة.")
        return redirect("home")
    form = ProductForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.seller = request.user
        obj.save()
        messages.success(request, "تم نشر المنتج.")
        return redirect("dashboard")
    return render(request, "form.html", {"form": form, "title": "إضافة منتج"})


@login_required
def supplier_product_add(request):
    if request.user.role != "supplier":
        return redirect("dashboard")
    if not request.user.is_verified:
        messages.error(request, "حساب المورّد بانتظار اعتماد الإدارة.")
        return redirect("home")
    form = SupplierProductForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.supplier = request.user
        obj.save()
        messages.success(request, "تمت إضافة منتج الجملة.")
        return redirect("dashboard")
    return render(request, "form.html", {"form": form, "title": "إضافة منتج للمورد"})


@login_required
def delivery_setup(request):
    if request.user.role != "delivery":
        return redirect("dashboard")
    company = getattr(request.user, "delivery_company", None)
    form = DeliveryCompanyForm(request.POST or None, request.FILES or None, instance=company)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.wilayas = form.cleaned_data["wilayas"]
        obj.save()
        messages.success(request, "تم حفظ ملف شركة التوصيل، وسيظهر بعد التحقق الإداري.")
        return redirect("dashboard" if request.user.is_verified else "home")
    return render(request, "form.html", {"form": form, "title": "ملف شركة التوصيل"})


def delivery_companies(request):
    q = request.GET.get("q", "").strip()
    qs = DeliveryCompany.objects.filter(verified=True).order_by("-rating")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return render(request, "delivery.html", {"companies": qs, "q": q})


@login_required
def contact_delivery(request, pk):
    company = get_object_or_404(DeliveryCompany, pk=pk, verified=True)
    if request.method == "POST":
        msg = request.POST.get("message", "").strip()[:2000]
        if msg:
            DeliveryContractRequest.objects.create(requester=request.user, company=company, message=msg)
            Notification.objects.create(user=company.owner, title="طلب تعاقد جديد", body=f"لديك طلب تعاقد من {request.user.username}.")
            messages.success(request, "تم إرسال طلب التواصل.")
        return redirect("delivery_companies")
    return render(request, "contact_delivery.html", {"company": company})


@login_required
def notifications(request):
    qs = request.user.notifications.order_by("-created_at")
    qs.filter(read=False).update(read=True)
    return render(request, "notifications.html", {"notifications": qs})


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    ip = request.META.get("REMOTE_ADDR", "unknown")
    cache_key = f"registration-attempts:{ip}"
    if request.method == "POST":
        attempts = cache.get(cache_key, 0)
        if attempts >= 5:
            messages.error(request, "تم تجاوز عدد محاولات التسجيل. حاول لاحقًا.")
            return render(request, "register.html", {"form": RegisterForm(), "limited": True}, status=429)
        cache.set(cache_key, attempts + 1, 60 * 60)
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save(commit=False)
        if user.role != "buyer":
            user.is_verified = False
        user.save()
        form.save_m2m()
        if user.role == "buyer":
            login(request, user)
            messages.success(request, "مرحبًا بك في NOVA MARKAT.")
            return redirect("dashboard")
        messages.success(request, "تم إنشاء الحساب. سيبقى دورك بانتظار اعتماد الإدارة قبل تفعيل وظائفه.")
        return redirect("login")
    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        ip = request.META.get("REMOTE_ADDR", "unknown")
        cache_key = f"login-attempts:{ip}"
        attempts = cache.get(cache_key, 0)
        if attempts >= 10:
            messages.error(request, "محاولات دخول كثيرة. انتظر 15 دقيقة ثم أعد المحاولة.")
            return render(request, "login.html", status=429)
        user = authenticate(request, username=request.POST.get("username", ""), password=request.POST.get("password", ""))
        if user is not None:
            cache.delete(cache_key)
            login(request, user)
            return redirect("dashboard")
        cache.set(cache_key, attempts + 1, 15 * 60)
        messages.error(request, "بيانات الدخول غير صحيحة.")
    return render(request, "login.html")


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")

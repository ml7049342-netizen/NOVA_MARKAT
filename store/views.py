from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404,redirect,render
from .forms import RegisterForm,ProductForm,SupplierProductForm,DeliveryCompanyForm
from .models import Product,DeliveryCompany,Notification,Order,OrderItem,DeliveryContractRequest,User,SupplierProduct,WILAYAS,Category,Review

def home(request):
    q=request.GET.get("q","").strip(); category=request.GET.get("category","")
    products=Product.objects.filter(active=True,stock__gt=0).select_related("seller","category")
    if q: products=products.filter(Q(name__icontains=q)|Q(description__icontains=q)|Q(seller__username__icontains=q))
    if category: products=products.filter(category_id=category)
    return render(request,"home.html",{"products":products[:60],"categories":Category.objects.filter(active=True),"q":q})

def product_detail(request,pk):
    product=get_object_or_404(Product,pk=pk,active=True)
    if request.method=="POST" and request.user.is_authenticated:
        try: rating=int(request.POST.get("rating",5))
        except (TypeError,ValueError): rating=5
        rating=max(1,min(5,rating)); comment=request.POST.get("comment","").strip()
        Review.objects.update_or_create(product=product,buyer=request.user,defaults={"rating":rating,"comment":comment})
        messages.success(request,"تم حفظ تقييمك."); return redirect("product_detail",pk=pk)
    return render(request,"product.html",{"product":product,"reviews":product.reviews.select_related("buyer")})

@require_POST
def add_to_cart(request,pk):
    get_object_or_404(Product,pk=pk,active=True)
    cart=request.session.get("cart",{}); key=str(pk); cart[key]=int(cart.get(key,0))+1; request.session["cart"]=cart
    return redirect("cart")

def cart(request):
    data=request.session.get("cart",{})
    if request.method=="POST":
        for key,val in request.POST.items():
            if key.startswith("qty_"):
                pid=key[4:]
                try: q=max(0,int(val))
                except: q=1
                if q: data[pid]=q
                else: data.pop(pid,None)
        request.session["cart"]=data
        return redirect("cart")
    products=Product.objects.filter(id__in=data.keys(),active=True); rows=[]; total=Decimal("0")
    for p in products:
        q=int(data[str(p.id)]); subtotal=p.price*q; total+=subtotal; rows.append((p,q,subtotal))
    return render(request,"cart.html",{"rows":rows,"total":total})

@login_required
@transaction.atomic
def checkout(request):
    data=request.session.get("cart",{})
    if not data: messages.error(request,"السلة فارغة."); return redirect("cart")
    if request.method=="POST":
        wilaya=request.POST.get("wilaya",""); address=request.POST.get("address","").strip(); phone=request.POST.get("phone","").strip()
        if not wilaya or not address or not phone: messages.error(request,"أكمل بيانات التوصيل."); return redirect("checkout")
        products=Product.objects.select_for_update().filter(id__in=data.keys(),active=True)
        order=Order.objects.create(buyer=request.user,wilaya=wilaya,address=address,phone=phone,payment_method="cash_on_delivery")
        total=Decimal("0")
        for p in products:
            q=int(data[str(p.id)])
            if q>p.stock: transaction.set_rollback(True); messages.error(request,f"الكمية غير متوفرة: {p.name}"); return redirect("cart")
            p.stock-=q; p.save(update_fields=["stock"]); OrderItem.objects.create(order=order,product=p,quantity=q,unit_price=p.price); total+=p.price*q
            Notification.objects.create(user=p.seller,title="طلب جديد",body=f"لديك طلب جديد #{order.id}.")
        order.total=total; order.save(update_fields=["total"]); request.session["cart"]={}
        Notification.objects.create(user=request.user,title="تم استلام طلبك",body=f"تم إنشاء الطلب #{order.id} والدفع عند الاستلام.")
        messages.success(request,f"تم إنشاء الطلب #{order.id}."); return redirect("orders")
    return render(request,"checkout.html",{"wilayas":WILAYAS})

@login_required
def orders(request):
    role=request.user.role
    base=Order.objects.prefetch_related("items__product").order_by("-created_at")
    if role=="seller": orders=base.filter(items__product__seller=request.user).distinct()
    elif role=="delivery":
        company=getattr(request.user,"delivery_company",None)
        orders=base.filter(delivery_company=company) if company else base.none()
    elif role=="supplier": orders=base.none()
    elif role=="admin" or request.user.is_superuser: orders=base
    else: orders=base.filter(buyer=request.user)
    return render(request,"orders.html",{"orders":orders})

@login_required
def dashboard(request):
    role=request.user.role
    if role=="seller":
        products=request.user.products.select_related("category"); items=OrderItem.objects.filter(product__seller=request.user); sales=sum((i.unit_price*i.quantity for i in items),Decimal("0"))
        return render(request,"dashboard_seller.html",{"products":products,"sales":sales,"orders_count":items.values("order_id").distinct().count()})
    if role=="supplier": return render(request,"dashboard_supplier.html",{"products":request.user.supplier_products.order_by("-id")})
    if role=="delivery":
        company=getattr(request.user,"delivery_company",None); requests=company.contract_requests.select_related("requester").order_by("-created_at") if company else []
        return render(request,"dashboard_delivery.html",{"company":company,"requests":requests})
    return render(request,"dashboard_buyer.html",{"orders":request.user.orders.order_by("-created_at")[:10]})

@login_required
def seller_product_add(request):
    if request.user.role!="seller": return redirect("dashboard")
    form=ProductForm(request.POST or None,request.FILES or None)
    if form.is_valid(): obj=form.save(commit=False); obj.seller=request.user; obj.save(); messages.success(request,"تم نشر المنتج."); return redirect("dashboard")
    return render(request,"form.html",{"form":form,"title":"إضافة منتج"})

@login_required
def supplier_product_add(request):
    if request.user.role!="supplier": return redirect("dashboard")
    form=SupplierProductForm(request.POST or None,request.FILES or None)
    if form.is_valid(): obj=form.save(commit=False); obj.supplier=request.user; obj.save(); messages.success(request,"تمت إضافة منتج الجملة."); return redirect("dashboard")
    return render(request,"form.html",{"form":form,"title":"إضافة منتج للمورد"})

@login_required
def delivery_setup(request):
    if request.user.role!="delivery": return redirect("dashboard")
    company=getattr(request.user,"delivery_company",None); form=DeliveryCompanyForm(request.POST or None,request.FILES or None,instance=company)
    if form.is_valid(): obj=form.save(commit=False); obj.owner=request.user; obj.wilayas=form.cleaned_data["wilayas"]; obj.save(); messages.success(request,"تم حفظ ملف شركة التوصيل، وسيظهر بعد التحقق الإداري."); return redirect("dashboard")
    return render(request,"form.html",{"form":form,"title":"ملف شركة التوصيل"})

def delivery_companies(request):
    q=request.GET.get("q","").strip(); qs=DeliveryCompany.objects.filter(verified=True).order_by("-rating")
    if q: qs=qs.filter(Q(name__icontains=q)|Q(description__icontains=q))
    return render(request,"delivery.html",{"companies":qs,"q":q})

@login_required
def contact_delivery(request,pk):
    company=get_object_or_404(DeliveryCompany,pk=pk,verified=True)
    if request.method=="POST":
        msg=request.POST.get("message","").strip()
        if msg: DeliveryContractRequest.objects.create(requester=request.user,company=company,message=msg); Notification.objects.create(user=company.owner,title="طلب تعاقد جديد",body=f"لديك طلب تعاقد من {request.user.username}."); messages.success(request,"تم إرسال طلب التواصل.")
        return redirect("delivery_companies")
    return render(request,"contact_delivery.html",{"company":company})

@login_required
def notifications(request):
    qs=request.user.notifications.order_by("-created_at"); qs.filter(read=False).update(read=True)
    return render(request,"notifications.html",{"notifications":qs})

def register(request):
    if request.user.is_authenticated: return redirect("dashboard")
    form=RegisterForm(request.POST or None)
    if form.is_valid(): user=form.save(); login(request,user); messages.success(request,"مرحبًا بك في NOVA MARKAT."); return redirect("dashboard")
    return render(request,"register.html",{"form":form})

def login_view(request):
    if request.method=="POST":
        user=authenticate(request,username=request.POST.get("username",""),password=request.POST.get("password",""))
        if user: login(request,user); return redirect("dashboard")
        messages.error(request,"بيانات الدخول غير صحيحة.")
    return render(request,"login.html")

def logout_view(request): logout(request); return redirect("home")

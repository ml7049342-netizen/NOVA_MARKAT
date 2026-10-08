from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from store import views
urlpatterns=[
 path("admin/",admin.site.urls),path("",views.home,name="home"),path("products/<int:pk>/",views.product_detail,name="product_detail"),
 path("cart/",views.cart,name="cart"),path("cart/add/<int:pk>/",views.add_to_cart,name="add_to_cart"),path("checkout/",views.checkout,name="checkout"),path("orders/",views.orders,name="orders"),
 path("dashboard/",views.dashboard,name="dashboard"),path("seller/products/add/",views.seller_product_add,name="seller_product_add"),path("supplier/products/add/",views.supplier_product_add,name="supplier_product_add"),
 path("delivery/",views.delivery_companies,name="delivery_companies"),path("delivery/setup/",views.delivery_setup,name="delivery_setup"),path("delivery/<int:pk>/contact/",views.contact_delivery,name="contact_delivery"),
 path("notifications/",views.notifications,name="notifications"),path("register/",views.register,name="register"),path("login/",views.login_view,name="login"),path("logout/",views.logout_view,name="logout"),
]+static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)

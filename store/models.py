from django.contrib.auth.models import AbstractUser
from django.db import models

ROLES = [("buyer","مشتري"),("seller","بائع"),("supplier","مورد"),("delivery","شركة توصيل"),("admin","إدارة")]
WILAYAS = [(str(i), f"ولاية {i}") for i in range(1,70)]

class User(AbstractUser):
    role=models.CharField(max_length=20,choices=ROLES,default="buyer")
    phone=models.CharField(max_length=30,blank=True)
    avatar=models.ImageField(upload_to="avatars/",blank=True,null=True)
    is_verified=models.BooleanField(default=False)

class DeliveryCompany(models.Model):
    owner=models.OneToOneField(User,on_delete=models.CASCADE,related_name="delivery_company")
    name=models.CharField(max_length=180)
    logo=models.ImageField(upload_to="delivery_logos/",blank=True,null=True)
    description=models.TextField(blank=True)
    wilayas=models.JSONField(default=list)
    cash_on_delivery=models.BooleanField(default=True)
    rating=models.DecimalField(max_digits=3,decimal_places=2,default=0)
    verified=models.BooleanField(default=False)
    phone=models.CharField(max_length=30,blank=True)
    def __str__(self): return self.name

class Category(models.Model):
    name=models.CharField(max_length=120)
    image=models.ImageField(upload_to="categories/",blank=True,null=True)
    active=models.BooleanField(default=True)
    def __str__(self): return self.name

class Product(models.Model):
    seller=models.ForeignKey(User,on_delete=models.CASCADE,related_name="products")
    category=models.ForeignKey(Category,on_delete=models.SET_NULL,null=True,blank=True)
    name=models.CharField(max_length=200)
    description=models.TextField()
    price=models.DecimalField(max_digits=12,decimal_places=2)
    stock=models.PositiveIntegerField(default=0)
    main_image=models.ImageField(upload_to="products/",blank=True,null=True)
    active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name="images")
    image=models.ImageField(upload_to="products/gallery/")
    alt_text=models.CharField(max_length=200,blank=True)

class SupplierProduct(models.Model):
    supplier=models.ForeignKey(User,on_delete=models.CASCADE,related_name="supplier_products")
    product_name=models.CharField(max_length=200)
    wholesale_price=models.DecimalField(max_digits=12,decimal_places=2)
    minimum_quantity=models.PositiveIntegerField(default=1)
    stock=models.PositiveIntegerField(default=0)
    image=models.ImageField(upload_to="supplier_products/",blank=True,null=True)
    description=models.TextField(blank=True)
    active=models.BooleanField(default=True)

class Order(models.Model):
    STATUS=[("new","جديد"),("confirmed","مؤكد"),("preparing","قيد التجهيز"),("shipped","خرج للتوصيل"),("delivered","تم التسليم"),("cancelled","ملغى")]
    buyer=models.ForeignKey(User,on_delete=models.PROTECT,related_name="orders")
    delivery_company=models.ForeignKey(DeliveryCompany,on_delete=models.SET_NULL,null=True,blank=True)
    status=models.CharField(max_length=20,choices=STATUS,default="new")
    wilaya=models.CharField(max_length=10,choices=WILAYAS)
    address=models.TextField()
    phone=models.CharField(max_length=30)
    total=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    payment_method=models.CharField(max_length=30,default="cash_on_delivery")
    created_at=models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name="items")
    product=models.ForeignKey(Product,on_delete=models.PROTECT)
    quantity=models.PositiveIntegerField()
    unit_price=models.DecimalField(max_digits=12,decimal_places=2)

class Notification(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="notifications")
    title=models.CharField(max_length=200)
    body=models.TextField()
    read=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name="reviews")
    buyer=models.ForeignKey(User,on_delete=models.CASCADE)
    rating=models.PositiveSmallIntegerField()
    comment=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=("product","buyer")

class DeliveryContractRequest(models.Model):
    STATUS=[("pending","قيد الانتظار"),("accepted","مقبول"),("rejected","مرفوض")]
    requester=models.ForeignKey(User,on_delete=models.CASCADE,related_name="delivery_requests")
    company=models.ForeignKey(DeliveryCompany,on_delete=models.CASCADE,related_name="contract_requests")
    message=models.TextField()
    status=models.CharField(max_length=20,choices=STATUS,default="pending")
    created_at=models.DateTimeField(auto_now_add=True)

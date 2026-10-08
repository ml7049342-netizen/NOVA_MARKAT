from django.contrib import admin
from .models import User,DeliveryCompany,Category,Product,ProductImage,SupplierProduct,Order,OrderItem,Notification,Review,DeliveryContractRequest
admin.site.register([User,DeliveryCompany,Category,Product,ProductImage,SupplierProduct,Order,OrderItem,Notification,Review,DeliveryContractRequest])

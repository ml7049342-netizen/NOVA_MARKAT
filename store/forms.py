from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Product, SupplierProduct, DeliveryCompany, Category, WILAYAS

class RegisterForm(UserCreationForm):
    email=forms.EmailField(required=True)
    phone=forms.CharField(max_length=30)
    role=forms.ChoiceField(choices=[x for x in User._meta.get_field("role").choices if x[0] != "admin"])
    class Meta:
        model=User; fields=("username","email","phone","role","password1","password2")

class ProductForm(forms.ModelForm):
    class Meta:
        model=Product; fields=("name","category","description","price","stock","main_image","active")

class SupplierProductForm(forms.ModelForm):
    class Meta:
        model=SupplierProduct; fields=("product_name","description","wholesale_price","minimum_quantity","stock","image","active")

class DeliveryCompanyForm(forms.ModelForm):
    wilayas=forms.MultipleChoiceField(choices=WILAYAS,required=False,widget=forms.CheckboxSelectMultiple)
    class Meta:
        model=DeliveryCompany; fields=("name","description","phone","cash_on_delivery","logo","wilayas")
    def clean_wilayas(self): return self.cleaned_data["wilayas"]

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Product, SupplierProduct, DeliveryCompany, Category, WILAYAS


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=30)
    role = forms.ChoiceField(
        choices=[choice for choice in User._meta.get_field("role").choices if choice[0] != "admin"]
    )

    class Meta:
        model = User
        fields = ("username", "email", "phone", "role", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("هذا البريد الإلكتروني مستخدم بالفعل.")
        return email


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ("name", "category", "description", "price", "stock", "main_image", "active")


class SupplierProductForm(forms.ModelForm):
    class Meta:
        model = SupplierProduct
        fields = ("product_name", "description", "wholesale_price", "minimum_quantity", "stock", "image", "active")


class DeliveryCompanyForm(forms.ModelForm):
    wilayas = forms.MultipleChoiceField(choices=WILAYAS, required=False, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = DeliveryCompany
        fields = ("name", "description", "phone", "cash_on_delivery", "logo", "wilayas")

    def clean_wilayas(self):
        return self.cleaned_data["wilayas"]


class ProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True, max_length=254)

    class Meta:
        model = User
        fields = ("username", "email", "phone", "avatar")
        widgets = {
            "username": forms.TextInput(attrs={"autocomplete": "username", "maxlength": 150}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "maxlength": 30}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        users = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise forms.ValidationError("هذا البريد الإلكتروني مستخدم بالفعل.")
        return email

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if not avatar or not hasattr(avatar, "read"):
            return avatar
        if avatar.size > 2 * 1024 * 1024:
            raise forms.ValidationError("حجم الصورة يجب ألا يتجاوز 2 ميغابايت.")
        try:
            from PIL import Image, UnidentifiedImageError
            avatar.seek(0)
            image = Image.open(avatar)
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise forms.ValidationError("الصيغ المدعومة هي JPG وPNG وWEBP فقط.")
            image.verify()
            avatar.seek(0)
        except forms.ValidationError:
            raise
        except Exception:
            raise forms.ValidationError("الملف المرفوع ليس صورة صالحة.")
        return avatar

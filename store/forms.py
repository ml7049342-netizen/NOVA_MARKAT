from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Product, SupplierProduct, DeliveryCompany, Category, WILAYAS


AVATAR_CHOICES = [
    ("avatar-1.svg", "الذهبي"),
    ("avatar-2.svg", "الوردي"),
    ("avatar-3.svg", "الأخضر"),
    ("avatar-4.svg", "الأزرق"),
    ("avatar-5.svg", "الكلاسيكي"),
]


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
    avatar_choice = forms.ChoiceField(choices=AVATAR_CHOICES, required=True)

    class Meta:
        model = User
        fields = ("username", "email", "phone")
        widgets = {
            "username": forms.TextInput(attrs={"autocomplete": "username", "maxlength": 150}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "maxlength": 30}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_avatar = getattr(self.instance, "avatar", None)
        current_name = getattr(current_avatar, "name", "") if current_avatar else ""
        preset_name = current_name.removeprefix("preset/")
        valid_choices = {value for value, _label in AVATAR_CHOICES}
        self.fields["avatar_choice"].initial = preset_name if preset_name in valid_choices else "avatar-1.svg"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        users = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise forms.ValidationError("هذا البريد الإلكتروني مستخدم بالفعل.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        choice = self.cleaned_data.get("avatar_choice", "avatar-1.svg")
        valid_choices = {value for value, _label in AVATAR_CHOICES}
        if choice not in valid_choices:
            raise ValueError("Invalid preset avatar choice")
        # Store only a stable preset identifier in the existing field; no uploaded file or migration needed.
        user.avatar = f"preset/{choice}"
        if commit:
            user.save()
            self.save_m2m()
        return user

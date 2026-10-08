# NOVA MARKAT
منصة تجارة إلكترونية جزائرية متعددة الأطراف: مشتري، بائع، مورد، شركة توصيل، وإدارة.

## أول تشغيل سريع للواجهة في المتصفح
ادخل إلى مجلد `browser_demo` ثم شغّل:

```bash
python -m http.server 8080
```

ثم افتح:

`http://127.0.0.1:8080`

هذه الواجهة تعمل مباشرة في المتصفح وتحتوي على تجربة متجر، بحث، سلة، طلب بالدفع عند الاستلام، لوحات أدوار، وشركات توصيل.

## تشغيل النسخة الخلفية Django
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations store
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## المسار المخطط
1. تثبيت واختبار موقع الويب.
2. ربط الواجهة بقاعدة بيانات Django بدل البيانات التجريبية.
3. استكمال لوحات الإدارة والرسائل والتعاقد والتوصيل.
4. إضافة اختبارات وأمان وإعدادات الإنتاج.
5. تحويل الواجهة إلى تطبيق Android/iOS عبر طبقة API مع الحفاظ على الحسابات والبيانات.

## ملاحظة
نسخة `browser_demo` هي واجهة متصفح عملية مستقلة لتجربة التصميم والتدفقات قبل ربطها بالـ backend. لا تعتبر نظامًا إنتاجيًا أو ضمانًا أمنيًا نهائيًا.

## النشر على Render
1. ارفع المشروع إلى مستودع GitHub (مجلد `nova_markat_src` في الجذر).
2. في Render: New ← Blueprint ← اختر المستودع؛ سيقرأ `render.yaml` وينشئ الخدمة وقاعدة PostgreSQL.
3. بعد أول نشر، من لوحة الخدمة ← Shell نفّذ: `python manage.py createsuperuser`.
ملاحظة: صور المنتجات المرفوعة تُحفظ على قرص مؤقت في الخطة المجانية وتُمحى عند إعادة النشر؛ للإنتاج استخدم تخزينًا دائمًا (S3 أو Cloudinary).

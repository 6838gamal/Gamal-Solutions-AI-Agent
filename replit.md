# جمال سولوشنز — منصة الذكاء الاصطناعي المؤسسي

منصة ذكاء اصطناعي مؤسسية كاملة مبنية بـ Python + FastAPI + Jinja2.

## هيكل المشروع

```
/
├── app/                    # تطبيق FastAPI الرئيسي
│   ├── core/               # الإعدادات، قاعدة البيانات، الأمان
│   ├── api/v1/             # مسارات API (JSON)
│   ├── web/                # مسارات الواجهة (HTML)
│   ├── templates/          # قوالب Jinja2 (HTML)
│   └── domains/            # النماذج والمنطق لكل وحدة
│       ├── auth/           # المصادقة والمستخدمون
│       ├── agents/         # وكلاء الذكاء الاصطناعي
│       ├── customers/      # CRM والعملاء
│       ├── conversations/  # المحادثات متعددة القنوات
│       ├── knowledge/      # قاعدة المعرفة
│       ├── workflows/      # سير العمل والمهام
│       ├── analytics/      # التحليلات
│       └── audit/          # سجل التدقيق
├── static/                 # الملفات الثابتة (CSS، favicon)
├── run.py                  # نقطة التشغيل
├── requirements.txt        # المتطلبات Python
└── Dockerfile              # Docker للنشر

```

## التشغيل

```bash
python3 run.py
```

التطبيق يعمل على: **http://localhost:5000**

## بيانات الدخول الافتراضية

| الحقل | القيمة |
|-------|--------|
| اسم المستخدم | `admin` |
| كلمة المرور | `Admin@2024!` |

## التقنيات المستخدمة

| الطبقة | التقنية |
|--------|---------|
| الخادم | FastAPI + Uvicorn |
| الواجهة | Jinja2 + Tailwind CSS (CDN) + HTMX |
| قاعدة البيانات | PostgreSQL (Render) عبر SQLAlchemy |
| المصادقة | JWT في Cookie آمن (HTTP-only) |
| النشر | Docker |

## الوحدات

| الوحدة | المسار |
|--------|--------|
| لوحة التحكم | `/dashboard` |
| وكلاء الذكاء الاصطناعي | `/agents` |
| العملاء CRM | `/customers` |
| المحادثات | `/conversations` |
| قاعدة المعرفة | `/knowledge` |
| سير العمل | `/workflows` |
| المهام | `/tasks` |
| التحليلات | `/analytics` |
| سجل التدقيق | `/audit` |
| المستخدمون | `/users` |
| الإعدادات | `/settings` |

## User Preferences

- Arabic RTL interface as primary language
- Enterprise-grade design with blue color scheme
- Cairo font for Arabic typography
- Pure Python/FastAPI — no React or Node.js

"""
Nishdot Web Platform — Base Settings
=====================================

Tüm ortamlarda (development, production) ortak olan ayarlar.
Ortama özel ayarlar development.py veya production.py'de override edilir.

Bu dosya TEK BAŞINA çalışmaz. Daima development.py veya production.py
tarafından import edilir.
"""

import environ
from pathlib import Path


# ==============================================================================
# Paths
# ==============================================================================

# settings/ dizininin iki üst dizini = proje kökü (nishdot-web/)
# Yol: nishdot-web/nishdot/settings/base.py → .parent.parent.parent = nishdot-web/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ==============================================================================
# MISCELLANEOUS
# ==============================================================================
# Add minor configuration settings here if needed

# ==============================================================================


# ==============================================================================
# Environment
# ==============================================================================

# django-environ ile .env dosyasından değişkenleri oku.
# Dosya bulunamazsa hata vermez — production'da ortam değişkenleri
# doğrudan sunucu konfigürasyonundan gelecek.
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

# ==============================================================================
# Core
# ==============================================================================

SECRET_KEY = env("DJANGO_SECRET_KEY")

# Kişisel veri (T.C. Kimlik No) şifreleme anahtarı — SECRET_KEY'den BAĞIMSIZ.
# Böylece SECRET_KEY rotasyonu şifreli verileri bozmaz. Bkz: core/crypto.py
FERNET_KEY = env("FERNET_KEY", default="")

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

ROOT_URLCONF = "nishdot.urls"

WSGI_APPLICATION = "nishdot.wsgi.application"

ASGI_APPLICATION = "nishdot.asgi.application"

# ==============================================================================
# Apps
# ==============================================================================

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
]

THIRD_PARTY_APPS = []

LOCAL_APPS = [
    "core",
    "users",
    "events",
    "jams",
    "pages",
    "dashboard",
]

# Sıralama önemli: Django built-in'ler → 3. parti → yerel uygulamalar.
# Bu sıra, template override mekanizmasının doğru çalışmasını sağlar.
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ==============================================================================
# Middleware
# ==============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ==============================================================================
# Templates
# ==============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Proje kökündeki templates/ dizinini global olarak tanı.
        # App'lerin kendi templates/ dizinleri APP_DIRS=True ile zaten taranır.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ==============================================================================
# Authentication
# ==============================================================================

# KRİTİK: Bu ayar ilk migration'dan önce tanımlanmalı.
# İlk migrate çalıştırıldıktan sonra değiştirmek son derece zahmetlidir.
AUTH_USER_MODEL = "users.CustomUser"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGIN_REDIRECT_URL = "users:dashboard"
LOGOUT_REDIRECT_URL = "pages:home"
LOGIN_URL = "users:login"

# ==============================================================================
# E-MAIL (SMTP) SETTINGS
# ==============================================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("SMTP_SERVER", default="smtp.gmail.com")
EMAIL_PORT = env("SMTP_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("SMTP_USERNAME", default="")
EMAIL_HOST_PASSWORD = env("SMTP_PASSWORD", default="")
DEFAULT_FROM_EMAIL = f"Nishdot <{EMAIL_HOST_USER}>"

# İkinci SMTP hesabı (Game Jam / İletişim formu geri bildirimleri).
# Tüm ortam değişkeni okumaları settings üzerinden yapılır — kod içinde
# os.getenv / decouple KULLANILMAZ (tek konfigürasyon mekanizması).
EMAIL2_HOST = env("SMTP2_SERVER", default="smtp.gmail.com")
EMAIL2_PORT = env("SMTP2_PORT", default=587, cast=int)
EMAIL2_HOST_USER = env("SMTP2_USERNAME", default="")
EMAIL2_HOST_PASSWORD = env("SMTP2_PASSWORD", default="")

# ==============================================================================
# Logging
# ==============================================================================

# Console handler: development'ta terminale, production'da Gunicorn üzerinden
# systemd journal'a (journalctl -u gunicorn) yazar. print() KULLANILMAZ.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ==============================================================================
# Internationalization & Localization
# ==============================================================================

# Admin paneli ve form validasyon mesajları Türkçe görünecek.
LANGUAGE_CODE = "tr"

# Tüm tarih/saat işlemleri İstanbul zaman diliminde.
TIME_ZONE = "Europe/Istanbul"

USE_I18N = True

USE_TZ = True

# ==============================================================================
# Static Files (CSS, JavaScript, Images)
# ==============================================================================

STATIC_URL = "/static/"

# Proje kökündeki static/ dizini — global statik dosyalar burada.
# App'lerin kendi static/ dizinleri Django tarafından otomatik taranır.
STATICFILES_DIRS = [BASE_DIR / "static"]

# ==============================================================================
# Media Files (Kullanıcı Yüklemeleri)
# ==============================================================================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ==============================================================================
# Default Primary Key
# ==============================================================================

# BigAutoField: 64-bit integer. Standart AutoField (32-bit) 2.1 milyar kayıtta
# taşar. BigAutoField ile bu limit 9.2 katrilyon — gelecek garantisi.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

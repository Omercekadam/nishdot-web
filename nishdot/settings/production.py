"""
Nishdot Web Platform — Production Settings
============================================

Canlı sunucu (SadeHost VDS) için güvenlik odaklı ayarlar.
base.py'deki ortak ayarları miras alır ve production'a özel
konfigürasyonları ekler/override eder.

Kullanım:
    DJANGO_SETTINGS_MODULE=nishdot.settings.production

Sunucu: Ubuntu VDS (2GB RAM, 40GB SSD), Nginx + Gunicorn
"""

from .base import *  # noqa: F401, F403
from .base import env


# ==============================================================================
# Core
# ==============================================================================

# Production'da DEBUG kesinlikle kapalı. Açık kalırsa:
# - Stack trace'ler kullanıcıya gösterilir (güvenlik açığı)
# - Statik dosyalar Django tarafından sunulur (performans felaketi)
# - Template hataları detaylı gösterilir (bilgi sızıntısı)
DEBUG = False

# ==============================================================================
# Database
# ==============================================================================

# PostgreSQL — production için zorunlu.
# DATABASE_URL formatı: postgres://USER:PASSWORD@HOST:PORT/DB_NAME
DATABASES = {
    "default": env.db("DATABASE_URL"),
}
DATABASES["default"]["CONN_MAX_AGE"] = 600  # 10 dakika connection pooling

# ==============================================================================
# Security
# ==============================================================================

# SSL Nginx'te sonlanır; Gunicorn'a unix soketten düz HTTP gelir.
# Bu başlık olmadan request.is_secure() False döner ve SECURE_SSL_REDIRECT
# sonsuz yönlendirme döngüsüne girer. Nginx tarafında mutlaka
# "proxy_set_header X-Forwarded-Proto $scheme;" tanımlı olmalıdır.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HTTPS zorunluluğu — HTTP isteklerini otomatik yönlendirir.
SECURE_SSL_REDIRECT = True

# Django 4+ HTTPS POST'larda Origin başlığını bu listeyle doğrular.
# Tanımlı olmazsa proxy arkasında CSRF reddi yaşanabilir.
CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=["https://nishdot.com.tr", "https://www.nishdot.com.tr"],
)

# Cookie'ler sadece HTTPS üzerinden gönderilir.
# Bu olmadan session hijacking mümkün olur.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Tarayıcıya "bu siteye sadece HTTPS ile bağlan" der (1 yıl cache).
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# XSS koruması (modern tarayıcılarda varsayılan, ama ek güvenlik katmanı).
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# ==============================================================================
# Caching (Redis)
# ==============================================================================

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Session engine olarak Redis kullanalım (daha hızlı oturum yönetimi)
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ==============================================================================
# Static Files
# ==============================================================================

# collectstatic komutu tüm statik dosyaları bu dizine toplar.
# Nginx bu dizini doğrudan sunar — Django'ya hiç uğramaz.
STATIC_ROOT = BASE_DIR / "staticfiles"

# Cache-busting: collectstatic her dosyaya içerik hash'i ekler
# (output.css → output.a1b2c3.css). Nginx'in 30 günlük cache'i olsa bile
# her deploy'da kullanıcılar yeni CSS/JS'i anında alır.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

# ==============================================================================
# Rate Limiting
# ==============================================================================

# Nginx arkasında REMOTE_ADDR proxy'nin kendi IP'sini gösterir.
# django-ratelimit gerçek istemci IP'sini bu header'dan okur.
# Nginx tarafında "proxy_set_header X-Real-IP $remote_addr;" tanımlı olmalıdır.
RATELIMIT_IP_META_KEY = "HTTP_X_REAL_IP"

# ==============================================================================
# Email
# ==============================================================================

# Production'da gerçek SMTP ayarları .env'den okunacak.
# Şimdilik varsayılan bırakılıyor, mail servisi entegre edildiğinde
# burada konfigüre edilecek.

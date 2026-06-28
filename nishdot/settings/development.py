"""
Nishdot Web Platform — Development Settings
=============================================

Yerel geliştirme ortamı için ayarlar.
base.py'deki ortak ayarları miras alır ve geliştirmeye özel
konfigürasyonları ekler/override eder.

Kullanım:
    DJANGO_SETTINGS_MODULE=nishdot.settings.development
"""

from .base import *  # noqa: F401, F403
from .base import INSTALLED_APPS, MIDDLEWARE, env


# ==============================================================================
# Core
# ==============================================================================

DEBUG = True

# ==============================================================================
# Database
# ==============================================================================

# Geliştirme ortamında SQLite — kurulum gerektirmez, hızlı başlangıç.
# Production'da PostgreSQL'e geçilecek (production.py'de tanımlı).
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),  # noqa: F405
}

# ==============================================================================
# Email
# ==============================================================================

# Gerçek mail göndermez, terminale yazar.
# Kayıt onayı, şifre sıfırlama gibi akışları test etmek için ideal.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ==============================================================================
# Django Debug Toolbar
# ==============================================================================

# Debug Toolbar: SQL sorgularını, template render sürelerini, cache
# kullanımını görselleştirir. N+1 sorgu problemlerini tespit etmek için
# vazgeçilmez bir araç.
INSTALLED_APPS += [
    "debug_toolbar",
    "django_extensions",
]

MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

# Docker veya WSL kullanılmadığı sürece bu yeterli.
INTERNAL_IPS = ["127.0.0.1"]

# ==============================================================================
# Static Files
# ==============================================================================

# Development'ta Django statik dosyaları kendisi sunar (DEBUG=True olduğunda).
# Production'da bu iş Nginx'e devredilir.

"""
Nishdot Web Platform — Root URL Configuration
===============================================

Tüm app URL'leri buradan dağıtılır.
Her app kendi urls.py dosyasını tanımlar ve buradan include edilir.
"""

from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from pages.sitemaps import SITEMAPS

urlpatterns = [
    # Ana sayfa ve statik sayfalar
    path("", include("pages.urls")),

    # Etkinlik Sayfaları
    path("events/", include("events.urls")),

    # Kullanıcı Kayıt & Giriş (Auth)
    path("auth/", include("users.urls")),

    # Custom Dashboard Panel
    path("management/", include("dashboard.urls")),

    # SEO: sitemap ve robots.txt
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain"), name="robots_txt"),

    # Admin paneli özel URL'de — varsayılan /admin/ brute-force hedefidir.
    # Bu basit değişiklik, otomatik bot saldırılarının %99'unu engeller.
    path("yonetim/", admin.site.urls),
]

# ==============================================================================
# Development-Only URL Patterns
# ==============================================================================

if settings.DEBUG:
    # Django Debug Toolbar — sadece development'ta aktif.
    # Production'da bu blok hiç çalışmaz (DEBUG=False).
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]

    # Development'ta Django statik ve media dosyalarını kendisi sunar.
    # Production'da bu iş Nginx'e bırakılır.
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

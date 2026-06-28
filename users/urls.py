"""
Users URL Configuration
========================

Kullanıcı ile ilgili URL pattern'ları burada tanımlanacak.
Şimdilik boş — login/logout URL'leri beta aşamasında eklenecek.

Root urls.py'den şu şekilde include edilecek:
    path("hesap/", include("users.urls")),
"""

from django.urls import path  # noqa: F401

app_name = "users"

urlpatterns = []

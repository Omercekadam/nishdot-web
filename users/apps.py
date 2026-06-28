"""
Users App — Kullanıcı Yönetimi
================================

Nishdot platformunun kullanıcı modeli, kimlik doğrulama ve
yetkilendirme altyapısını sağlar.
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = "Kullanıcılar"

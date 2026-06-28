"""
Users Admin Configuration
==========================

CustomUser modelinin Django admin panelinde düzgün görünmesi ve
yönetilebilmesi için gerekli konfigürasyon.

Django'nun varsayılan UserAdmin'i, standart User modeline göre
tasarlanmıştır. Custom alanlar (email unique vb.) eklendiğinde
bu konfigürasyon güncellenmezse admin paneli hata verir veya
alanları göstermez.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    CustomUser için admin panel konfigürasyonu.

    UserAdmin'den miras alarak Django'nun tüm kullanıcı yönetim
    arayüzünü (şifre değiştirme, izin yönetimi vb.) korur.
    Sadece custom alanlara göre fieldsets ve list_display güncellenir.
    """

    # Liste görünümünde gösterilecek sütunlar
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_staff",
        "date_joined",
    )

    # Sağ kenar çubuğundaki filtreler
    list_filter = ("role", "is_staff", "is_superuser", "is_active")

    # Arama alanı — bu alanlar üzerinden arama yapılabilir
    search_fields = ("username", "email", "first_name", "last_name", "university", "department")

    # Varsayılan sıralama
    ordering = ("-date_joined",)

    # Düzenleme formundaki alan grupları
    fieldsets = UserAdmin.fieldsets + (
        (
            "Rol ve Profil",
            {
                "fields": (
                    "role",
                    "university",
                    "department",
                    "portfolio_url",
                )
            },
        ),
    )

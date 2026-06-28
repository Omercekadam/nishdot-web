"""
Core App — Paylaşılan Altyapı
===============================

Projedeki tüm app'lerin ortak kullanacağı soyut modeller,
yardımcı fonksiyonlar ve araçlar burada tanımlanır.

Bu app'in kendine ait view'ları veya URL'leri yoktur.
Amacı DRY (Don't Repeat Yourself) prensibini desteklemektir.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Çekirdek Altyapı"

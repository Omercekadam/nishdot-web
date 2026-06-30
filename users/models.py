"""
Custom User Model
==================

Django'nun varsayılan User modelini genişleten özel kullanıcı modeli.

Neden Custom User Model?
-------------------------
Django dokümantasyonu, projenin EN BAŞINDA custom user model tanımlamayı
şiddetle önerir. Çünkü:
  1. AUTH_USER_MODEL ilk migration'dan sonra değiştirmek son derece zahmetli
  2. İleride email ile giriş, profil alanları, rol sistemi gibi
     özellikler eklemek kaçınılmaz
  3. Şimdi yapmak 5 dakika, sonra yapmak saatlerce sürer

Neden AbstractUser (AbstractBaseUser değil)?
---------------------------------------------
AbstractUser, Django'nun tüm standart alanlarını hazır getirir:
  - username, email, first_name, last_name
  - is_active, is_staff, is_superuser
  - date_joined, last_login
  - Şifre hash'leme ve doğrulama
  - Grup ve izin sistemi entegrasyonu

AbstractBaseUser ise tamamen boş bir sayfa — her şeyi sıfırdan yazmak
gerekir. Bu proje için gereksiz bir karmaşıklık.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import TimeStampedModel

from .managers import CustomUserManager


class CustomUser(AbstractUser, TimeStampedModel):
    """
    Nishdot platformu kullanıcı modeli.

    AbstractUser'dan gelen tüm standart alanları miras alır.
    TimeStampedModel'dan created_at ve updated_at alanlarını alır.

    Şimdilik sadece email alanı unique yapılmış durumda.
    Rol sistemi, profil bilgileri gibi ek alanlar site detayları
    netleştikten sonra bu modele eklenecek.

    Note:
        AbstractUser'ın kendi date_joined alanı var ama bu auto_now_add
        kullanmaz. TimeStampedModel'ın created_at alanı daha tutarlı
        bir zaman damgası sağlar. İkisi bir arada sorun çıkarmaz.
    """

    class Role(models.TextChoices):
        MEMBER = "member", "Kulüp Üyesi"
        BOARD  = "board",  "Yönetim Kurulu"
        ADMIN  = "admin",  "Yönetici"

    email = models.EmailField(
        unique=True,
        verbose_name="E-posta adresi",
        help_text="Benzersiz bir e-posta adresi giriniz.",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        verbose_name="Rol"
    )

    # ── Profil Alanları ──
    is_verified = models.BooleanField(default=False, verbose_name="Doğrulandı mı?")
    verification_code = models.CharField(max_length=6, blank=True, null=True, verbose_name="Doğrulama Kodu")
    code_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Kod Geçerlilik Süresi")

    phone_number = models.CharField(max_length=20, blank=True, verbose_name="Telefon Numarası")
    national_id = models.CharField(max_length=11, blank=True, verbose_name="T.C. Kimlik Numarası")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Doğum Tarihi")
    university = models.CharField(max_length=200, blank=True, verbose_name="Üniversite")
    department = models.CharField(max_length=200, blank=True, verbose_name="Bölüm")
    portfolio_url = models.TextField(blank=True, verbose_name="Portfolyo Linkleri")

    # Custom manager'ı kullan
    objects = CustomUserManager()

    class Meta:
        verbose_name = "Kullanıcı"
        verbose_name_plural = "Kullanıcılar"
        ordering = ["-date_joined"]

    @property
    def is_board_member(self):
        """Kullanıcının yönetim kurulu veya yönetici olup olmadığını döndürür."""
        return self.role in (self.Role.BOARD, self.Role.ADMIN)

    @property
    def is_admin_user(self):
        """Kullanıcının tam yetkili yönetici olup olmadığını döndürür."""
        return self.role == self.Role.ADMIN

    def __str__(self):
        """
        Admin panelinde ve shell'de kullanıcının nasıl görüneceğini belirler.
        Kullanıcı adı yoksa email gösterilir.
        """
        return self.get_full_name() or self.username

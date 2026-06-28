"""
Custom User Manager
====================

Django'nun varsayılan UserManager'ı username alanını zorunlu tutar.
Bizim modelimizde username opsiyonel olabilir veya farklı alanlar
gerekebilir. Bu manager, kullanıcı oluşturma mantığını
özelleştirmemizi sağlar.

create_user() ve create_superuser() metotları Django'nun iç
mekanizmaları tarafından çağrılır:
  - createsuperuser management komutu
  - Admin panelinden kullanıcı oluşturma
  - Programatik kullanıcı oluşturma
"""

from django.contrib.auth.base_user import BaseUserManager


class CustomUserManager(BaseUserManager):
    """
    Email alanını normalize eden ve tutarlı kullanıcı oluşturma
    sağlayan custom manager.
    """

    def create_user(self, username, email, password=None, **extra_fields):
        """
        Standart kullanıcı oluşturur.

        Args:
            username: Kullanıcı adı.
            email: E-posta adresi (zorunlu, unique).
            password: Şifre (hash'lenerek saklanır).
            **extra_fields: Modeldeki diğer alanlar.

        Returns:
            Oluşturulan CustomUser instance.

        Raises:
            ValueError: email boş bırakıldığında.
        """
        if not email:
            raise ValueError("E-posta adresi zorunludur.")

        # normalize_email(): domain kısmını küçük harfe çevirir.
        # Örn: "User@EXAMPLE.COM" → "User@example.com"
        # Lokal kısma (@ öncesi) dokunmaz çünkü RFC 5321'e göre
        # case-sensitive olabilir.
        email = self.normalize_email(email)

        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)  # Şifreyi hash'leyerek saklar
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        """
        Tam yetkili yönetici kullanıcı oluşturur.

        createsuperuser komutu bu metodu çağırır.
        is_staff ve is_superuser alanlarını True'ya zorlar.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser için is_staff=True zorunludur.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser için is_superuser=True zorunludur.")

        return self.create_user(username, email, password, **extra_fields)

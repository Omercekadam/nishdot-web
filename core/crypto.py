"""
Kişisel Veri Şifreleme Yardımcıları
====================================

T.C. Kimlik Numarası gibi hassas kişisel verilerin (KVKK) şifrelenmesi ve
tekillik kontrolü için ortak fonksiyonlar. JamApplication ve EventApplication
modelleri bu modülü kullanır.

Anahtar yönetimi:
    - FERNET_KEY: .env'de tanımlı, SECRET_KEY'den BAĞIMSIZ bir anahtar.
      Böylece SECRET_KEY rotasyonu şifreli verileri etkilemez.
    - Anahtar üretmek için:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    - FERNET_KEY rotasyonu gerekirse önce tüm kayıtları eski anahtarla çözüp
      yenisiyle şifreleyen bir data migration yazılmalıdır.
"""

import base64
import hashlib
import hmac

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet

# Fernet token'ları her zaman bu önekle başlar (version byte 0x80'in base64'ü).
# Bir değerin şifrelenmiş olup olmadığını anlamak için kullanılır.
FERNET_TOKEN_PREFIX = "gAAAA"


def get_fernet() -> Fernet:
    """FERNET_KEY ortam değişkeninden Fernet nesnesi üretir."""
    key = getattr(settings, "FERNET_KEY", "")
    if not key:
        raise ImproperlyConfigured(
            "FERNET_KEY tanımlı değil. .env dosyanıza FERNET_KEY ekleyin. "
            "Üretmek için: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode("utf-8") if isinstance(key, str) else key)


def get_legacy_fernet() -> Fernet:
    """
    Eski şifreleme anahtarı (SECRET_KEY'den türetilen).
    SADECE eski kayıtları yeni anahtara taşıyan data migration'lar kullanır.
    """
    key = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def is_encrypted(value: str) -> bool:
    """Değerin zaten şifrelenmiş bir Fernet token'ı olup olmadığını döndürür."""
    return bool(value) and value.startswith(FERNET_TOKEN_PREFIX)


def encrypt_value(value: str) -> str:
    """Düz metni FERNET_KEY ile şifreler."""
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str) -> str:
    """Şifreli değeri çözer. Şifreli değilse olduğu gibi döndürür."""
    if not is_encrypted(value):
        return value
    return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")


def hash_national_id(national_id: str) -> str:
    """
    Tekillik kontrolü için HMAC-SHA256 özeti (64 karakter hex).

    Düz SHA-256 kullanılmaz: 11 haneli, checksum'lı bir sayı uzayı
    tuzsuz hash ile dakikalar içinde geri çevrilebilir. HMAC'in gizli
    anahtarı olmadan özetten kimlik numarasına dönmek mümkün değildir.
    """
    key = getattr(settings, "FERNET_KEY", "") or settings.SECRET_KEY
    return hmac.new(
        key.encode("utf-8"),
        national_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def is_valid_national_id(value: str) -> bool:
    """T.C. Kimlik Numarası için temel biçim kontrolü (11 hane, rakam, 0 ile başlamaz)."""
    return bool(value) and len(value) == 11 and value.isdigit() and value[0] != "0"

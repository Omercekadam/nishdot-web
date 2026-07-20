"""
T.C. Kimlik No şifreleme anahtarı geçişi (data migration).

Bu migration:
  1. JamApplication kayıtlarını ESKİ anahtardan (SECRET_KEY türevli) yeni
     bağımsız FERNET_KEY'e yeniden şifreler.
  2. EventApplication'daki DÜZ METİN T.C. Kimlik numaralarını şifreler
     (eskiden hiç şifrelenmiyordu — KVKK ihlali).
  3. Tekillik hash'lerini tuzsuz SHA-256'dan HMAC-SHA256'ya yükseltir.

ÇALIŞTIRMADAN ÖNCE:
  - .env dosyasında FERNET_KEY tanımlı olmalıdır.
  - SECRET_KEY henüz ROTASYON EDİLMEMİŞ olmalıdır (eski verinin çözülebilmesi
    için gereklidir). SECRET_KEY rotasyonu bu migration'dan SONRA yapılır.
"""

import hashlib
import hmac

from django.conf import settings
from django.db import migrations

FERNET_TOKEN_PREFIX = "gAAAA"


def _legacy_fernet():
    import base64
    from cryptography.fernet import Fernet
    key = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def _new_fernet():
    from cryptography.fernet import Fernet
    key = getattr(settings, "FERNET_KEY", "")
    if not key:
        raise RuntimeError(
            "FERNET_KEY tanımlı değil. Migration çalışmadan önce .env dosyanıza "
            "FERNET_KEY ekleyin."
        )
    return Fernet(key.encode("utf-8") if isinstance(key, str) else key)


def _hmac_hash(national_id):
    key = getattr(settings, "FERNET_KEY", "") or settings.SECRET_KEY
    return hmac.new(key.encode("utf-8"), national_id.encode("utf-8"), hashlib.sha256).hexdigest()


def _plaintext(value, legacy, new):
    """Değerin düz metin T.C. Kimlik No halini döndürür (çözülemezse None)."""
    if not value:
        return None
    if value.startswith(FERNET_TOKEN_PREFIX):
        for fernet in (new, legacy):  # önce yeni (zaten taşınmışsa), sonra eski
            try:
                return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
            except Exception:
                continue
        return None
    # Düz metin (ör. eski EventApplication kayıtları)
    return value


def reencrypt(apps, schema_editor):
    JamApplication = apps.get_model("jams", "JamApplication")
    EventApplication = apps.get_model("events", "EventApplication")

    # Kayıt yoksa anahtar üretmeye gerek yok — sessizce geç.
    if not JamApplication.objects.exists() and not EventApplication.objects.exists():
        return

    legacy = _legacy_fernet()
    new = _new_fernet()

    for Model in (JamApplication, EventApplication):
        for obj in Model.objects.all():
            plain = _plaintext(obj.national_id, legacy, new)
            if not plain:
                continue
            obj.national_id = new.encrypt(plain.encode("utf-8")).decode("utf-8")
            obj.national_id_hash = _hmac_hash(plain)
            obj.save(update_fields=["national_id", "national_id_hash"])


def noop_reverse(apps, schema_editor):
    # Geri alma anlamlı değil (anahtar geçişi geri döndürülemez).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("jams", "0007_remove_gamejam_is_applications_open"),
        ("events", "0008_eventimage"),
    ]

    operations = [
        migrations.RunPython(reencrypt, noop_reverse),
    ]

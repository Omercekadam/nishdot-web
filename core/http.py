"""
İstemci IP Adresi Yardımcıları
===============================

SecurityLog kayıtlarının, django-ratelimit ile AYNI IP kaynağını kullanmasını
sağlar. Bu iki yer ayrışırsa panelde görünen IP ile hız sınırının saydığı IP
farklı olur ve loglar işe yaramaz hâle gelir.
"""

from django.conf import settings

# GenericIPAddressField boş string kabul etmez (PostgreSQL'de inet tipi
# DataError verir). Hiçbir kaynak IP vermezse bu sentinel yazılır — kayıt
# kaybolmaktansa "bilinmiyor" olarak görünmesi yeğdir.
FALLBACK_IP = "0.0.0.0"


def get_client_ip(request):
    """
    İsteğin gerçek istemci IP adresini döndürür.

    Nginx arkasında REMOTE_ADDR proxy'nin kendi adresini gösterir (unix soket
    kullanılıyorsa boş string). Production ayarlarında django-ratelimit
    RATELIMIT_IP_META_KEY üzerinden X-Real-IP okur; bu fonksiyon aynı ayarı
    izleyerek iki taraf arasındaki tutarsızlığı ortadan kaldırır.

    Args:
        request: Django HttpRequest nesnesi.

    Returns:
        Boş olmayan bir IP adresi string'i. Hiçbir kaynak değer vermezse
        FALLBACK_IP döner.
    """
    meta_key = getattr(settings, "RATELIMIT_IP_META_KEY", "") or "REMOTE_ADDR"

    raw = request.META.get(meta_key) or request.META.get("REMOTE_ADDR") or ""

    # X-Forwarded-For biçimindeki başlıklar "istemci, proxy1, proxy2" olabilir;
    # zincirin ilk adresi gerçek istemcidir.
    ip = raw.split(",")[0].strip()

    return ip or FALLBACK_IP

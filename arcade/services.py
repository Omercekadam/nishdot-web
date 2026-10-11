"""
Liderlik Tablosu
=================

Kurallar:
    - Kapsam: yarışma penceresinde (starts_at ≤ created_at ≤ ends_at),
      sahiplenilmiş (user dolu) ve diskalifiye edilmemiş koşular.
    - Her oyuncunun EN İYİ skoru sayılır; eşitlikte o skora DAHA ÖNCE ulaşan üstte.

Uygulama: koşular (-score, created_at) sırasıyla okunur, her oyuncunun ilk
görülen kaydı alınır. Stand haftası ölçeğinde (yüzler/binler) yeterince hızlı;
gerekirse sonradan önbelleklenir.
"""

from .models import Competition, GameRun

TABLE_SIZE = 10

# Python'un upper()'ı Türkçe bilmez: "i".upper() == "I" (doğrusu "İ").
_TR_UPPER = {"i": "İ", "ı": "I"}


def display_name(user):
    """Tabloda görünen ad: "Ömer S." — ad + soyadın Türkçe büyütülmüş baş harfi."""
    ad = (user.first_name or "").strip()
    if not ad:
        return "Oyuncu"
    soyad = (user.last_name or "").strip()
    if not soyad:
        return ad
    bas_harf = _TR_UPPER.get(soyad[0], soyad[0].upper())
    return f"{ad} {bas_harf}."


def leaderboard(competition, limit=TABLE_SIZE, user=None):
    """
    Döner: {"tablo": [{"sira", "ad", "skor", "bu_sen_misin"}, ...],
            "sen": {"sira", "en_iyi"} | None}
    """
    kosular = (
        GameRun.objects
        .filter(
            created_at__gte=competition.starts_at,
            created_at__lte=competition.ends_at,
            user__isnull=False,
            is_disqualified=False,
        )
        .select_related("user")
        .order_by("-score", "created_at")
    )
    user_id = user.pk if user is not None and user.is_authenticated else None

    tablo, sen, gorulen = [], None, set()
    for kosu in kosular.iterator():
        if kosu.user_id in gorulen:
            continue
        gorulen.add(kosu.user_id)
        sira = len(gorulen)
        bu_sen = kosu.user_id == user_id
        if sira <= limit:
            tablo.append({
                "sira": sira,
                "ad": display_name(kosu.user),
                "skor": kosu.score,
                "bu_sen_misin": bu_sen,
            })
        if bu_sen:
            sen = {"sira": sira, "en_iyi": kosu.score}
        if sira >= limit and (user_id is None or sen is not None):
            break
    return {"tablo": tablo, "sen": sen}


def home_context(user):
    """Ana sayfa oyun bölümünün bağlamı; oyun kapalıysa None."""
    competition = Competition.current()
    if competition is None:
        return None
    status = competition.status
    tablo = {"tablo": [], "sen": None}
    if status != Competition.Status.UPCOMING:
        tablo = leaderboard(competition, user=user)
    return {"competition": competition, "status": status, **tablo}

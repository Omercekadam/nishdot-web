"""
Matchmaker Servisi
===================

"Ekip arıyorum" diyen jam başvurucularını rollere göre gruplayarak yönetim
kuruluna takım ÖNERİSİ üretir. Öneriler otomatik onaylanmaz — panelden
incelenip onaylanır veya reddedilir (bkz. SuggestedTeam.Status).

Algoritma sabit bir takım şeması aramaz; "eksik rol tamamlama" mantığıyla
çalışır: her turda mevcut rollerden birer kişi alınarak mümkün olduğunca
çeşitli bir takım kurulur.
"""

from collections import defaultdict

from django.db import transaction

from .models import GameJam, JamApplication, SuggestedTeam

# Rolü boş bırakılmış başvurular için grup anahtarı.
ROLSUZ = "Belirtilmemiş"

# Tek kişilik "takım" önerilmez — bu sayının altındaki grup dağıtılır.
MIN_TAKIM_BOYUTU = 2


def run_matchmaker(jam: GameJam) -> list[SuggestedTeam]:
    """
    Jam için takım önerileri üretir.

    Yalnızca team_status="looking" olan, henüz bir takıma atanmamış ve
    REDDEDİLMEMİŞ başvurular değerlendirilir. Tekrar çağrıldığında önceki
    takımlara dokunmaz, yalnızca boştaki başvuruları eşleştirir.

    Args:
        jam: Eşleştirmenin çalıştırılacağı GameJam.

    Returns:
        Bu çağrıda oluşturulan SuggestedTeam listesi (mevcut takımlar dâhil değil).
    """
    basvurular = list(
        JamApplication.objects
        .filter(
            jam=jam,
            team_status=JamApplication.TeamStatus.LOOKING,
            suggested_team__isnull=True,
        )
        .exclude(status=JamApplication.ApplicationStatus.REJECTED)
        .order_by("created_at")
    )

    if not basvurular:
        return []

    rol_gruplari = defaultdict(list)
    for basvuru in basvurular:
        rol_gruplari[basvuru.jam_role or ROLSUZ].append(basvuru)

    olusturulanlar = []
    # Sayaç döngü DIŞINDA bir kez okunur. Eski kod her turda count() çağırıp
    # üstüne len(olusturulanlar) eklediği için takım adları 1, 3, 5... diye
    # atlıyordu.
    sira = jam.suggested_teams.count()

    with transaction.atomic():
        while True:
            dolu_roller = [rol for rol, grup in rol_gruplari.items() if grup]
            if not dolu_roller:
                break

            uyeler = []
            for rol in dolu_roller:
                if len(uyeler) >= jam.max_team_size:
                    break
                uyeler.append(rol_gruplari[rol].pop(0))

            if len(uyeler) < MIN_TAKIM_BOYUTU:
                # Eşleşecek kimse kalmadı: tek kişiyi listeye geri koyup çık.
                artan = uyeler[0]
                rol_gruplari[artan.jam_role or ROLSUZ].insert(0, artan)
                break

            sira += 1
            takim = SuggestedTeam.objects.create(jam=jam, name=f"Takım {sira}")

            # Toplu update: üye başına ayrı save() çağırmak yerine tek sorgu.
            # JamApplication.save() içindeki şifreleme mantığı da atlanmış olur
            # (zaten şifreli veriye tekrar dokunmaya gerek yok).
            JamApplication.objects.filter(
                id__in=[uye.id for uye in uyeler]
            ).update(suggested_team=takim)

            olusturulanlar.append(takim)

    return olusturulanlar


def reset_matchmaker(jam: GameJam) -> int:
    """
    Jam'in tüm takım önerilerini siler ve üyelerin bağlantısını çözer.

    Başvuru kayıtlarına DOKUNMAZ — yalnızca öneri katmanı temizlenir.
    JamApplication.suggested_team alanı on_delete=SET_NULL olduğu için
    takımlar silindiğinde bağlantı otomatik çözülür.

    Args:
        jam: Sıfırlanacak GameJam.

    Returns:
        Silinen takım sayısı.
    """
    with transaction.atomic():
        takimlar = SuggestedTeam.objects.filter(jam=jam)
        sayi = takimlar.count()
        takimlar.delete()
    return sayi

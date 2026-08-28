"""
Saklama süresi dolan kişisel verileri siler (KVKK m.7 — imha yükümlülüğü).

    python manage.py purge_expired_data --dry-run   # önce ne silineceğini gör
    python manage.py purge_expired_data             # gerçekten sil

Süreler KVKK Aydınlatma Metni'nde ilan edilen değerlerle birebir aynıdır
(bkz. load_legal_documents.py). Metindeki süre değişirse buradaki sabitler de
güncellenmelidir.

Ayda bir çalıştırılması yeterlidir. Sunucuda cron'a eklemek için:
    0 4 1 * *  cd /var/www/nishdot-web && venv/bin/python manage.py purge_expired_data
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

# Aydınlatma metninde ilan edilen saklama süreleri
SAGLIK_IS_GUNU = 7      # sağlık verisi: etkinlik bitiminden sonra 7 iş günü
GENEL_GUN = 365         # diğer tüm başvuru verileri: 1 yıl


def is_gunu_ekle(tarih, gun_sayisi):
    """Verilen tarihe N iş günü ekler (hafta sonlarını atlar)."""
    kalan = gun_sayisi
    sonuc = tarih
    while kalan > 0:
        sonuc += timedelta(days=1)
        if sonuc.weekday() < 5:      # 0-4 = Pazartesi-Cuma
            kalan -= 1
    return sonuc


class Command(BaseCommand):
    help = "Saklama süresi dolan kişisel verileri siler (KVKK m.7)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Hiçbir şey silme, yalnızca neyin silineceğini listele.",
        )

    def handle(self, *args, **options):
        kuru = options["dry_run"]
        simdi = timezone.now()

        if kuru:
            self.stdout.write(self.style.WARNING("KURU ÇALIŞMA — hiçbir kayıt silinmeyecek.\n"))

        self._saglik_verilerini_sil(simdi, kuru)
        self._suresi_dolan_basvurulari_sil(simdi, kuru)

        if kuru:
            self.stdout.write(self.style.WARNING("\nKuru çalışma bitti. Gerçekten silmek için --dry-run olmadan çalıştırın."))
        else:
            self.stdout.write(self.style.SUCCESS("\nTemizlik tamamlandı."))

    # ------------------------------------------------------------------ #

    def _saglik_verilerini_sil(self, simdi, kuru):
        """Sağlık verisi özel nitelikli: etkinlik bitiminden 7 iş günü sonra silinir."""
        from jams.models import JamApplication

        adaylar = (
            JamApplication.objects
            .filter(health_purged_at__isnull=True)
            .exclude(health_notes="")
            .select_related("jam__event")
        )

        silinecek = []
        for basvuru in adaylar:
            bitis = basvuru.jam.event.end_date
            if bitis and simdi >= is_gunu_ekle(bitis, SAGLIK_IS_GUNU):
                silinecek.append(basvuru)

        self.stdout.write(f"Sağlık verisi ({SAGLIK_IS_GUNU} iş günü): {len(silinecek)} kayıt")
        for basvuru in silinecek:
            self.stdout.write(f"    - #{basvuru.id} {basvuru.jam.event.title}")
            if not kuru:
                basvuru.health_notes = ""
                basvuru.health_consent = False
                basvuru.health_purged_at = simdi
                basvuru.save(update_fields=["health_notes", "health_consent", "health_purged_at"])

    def _suresi_dolan_basvurulari_sil(self, simdi, kuru):
        """1 yılı dolan başvuru kayıtları tamamen silinir (T.C. kimlik dâhil)."""
        from events.models import EventApplication
        from jams.models import JamApplication

        sinir = simdi - timedelta(days=GENEL_GUN)

        jam_kayitlari = [
            b for b in JamApplication.objects.select_related("jam__event")
            if b.jam.event.end_date and b.jam.event.end_date < sinir
        ]
        etkinlik_kayitlari = [
            b for b in EventApplication.objects.select_related("event")
            if b.event.end_date and b.event.end_date < sinir
        ]

        toplam = len(jam_kayitlari) + len(etkinlik_kayitlari)
        self.stdout.write(f"Süresi dolan başvurular ({GENEL_GUN} gün): {toplam} kayıt")
        self.stdout.write(f"    jam başvurusu: {len(jam_kayitlari)}, etkinlik başvurusu: {len(etkinlik_kayitlari)}")

        if not kuru:
            for b in jam_kayitlari:
                b.delete()
            for b in etkinlik_kayitlari:
                b.delete()

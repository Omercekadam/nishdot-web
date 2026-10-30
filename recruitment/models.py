"""
Yönetim Kurulu Alımı — Veri Modeli
===================================

RecruitmentRound: bir alım dönemi ("2026-2027 Yönetim Kurulu") ve aç/kapa
                  anahtarı. Açıkken ana sayfada duyuru ve /basvuru/ formu görünür;
                  karargahtan kapatılınca ikisi de kalkar.
BoardApplication: bir üyenin o döneme başvurusu. Ad, soyad ve e-posta hesaptan
                  okunur, burada tekrar saklanmaz. Her üye her döneme bir kez başvurur.
"""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class RecruitmentRound(TimeStampedModel):
    title = models.CharField(max_length=120, verbose_name="Başlık", help_text='Ör. "2026-2027 Yönetim Kurulu"')
    is_open = models.BooleanField(default=False, verbose_name="Başvurular açık")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Alım dönemi"
        verbose_name_plural = "Alım dönemleri"

    def __str__(self):
        return self.title

    @classmethod
    def current(cls):
        """Karargahta yönetilen dönem: en son oluşturulan."""
        return cls.objects.order_by("-created_at").first()

    @classmethod
    def current_open(cls):
        """Başvuru alan dönem; yoksa None (form ve duyuru kapalı)."""
        return cls.objects.filter(is_open=True).order_by("-created_at").first()


class BoardApplication(TimeStampedModel):
    class Grade(models.TextChoices):
        PREP = "hazirlik", "Hazırlık"
        FIRST = "1", "1. Sınıf"
        SECOND = "2", "2. Sınıf"
        THIRD = "3", "3. Sınıf"
        FOURTH = "4", "4. Sınıf"

    class Position(models.TextChoices):
        # Kodlar birbirinin alt dizgisi değildir; virgüllü alanda __contains ile süzülebilir.
        EVENTS = "etkinlik", "Etkinlik ve Organizasyon Ekibi"
        SOCIAL = "sosyal_medya", "Sosyal Medya İçerik Üretimi"
        COMMUNITY = "topluluk", "Topluluk Sorumlusu"
        DESIGN = "tasarim", "Tasarım / Animasyon"
        TECH = "teknik", "Teknik Ekip / Proje Geliştirme"

    class WeeklyHours(models.TextChoices):
        UNDER_2 = "0-2", "2 saatten az"
        H2_5 = "2-5", "2–5 saat"
        H5_10 = "5-10", "5–10 saat"
        OVER_10 = "10+", "10 saatten fazla"

    class Status(models.TextChoices):
        PENDING = "beklemede", "Beklemede"
        INTERVIEW = "mulakat", "Mülakat"
        ACCEPTED = "kabul", "Kabul"
        REJECTED = "ret", "Ret"

    round = models.ForeignKey(RecruitmentRound, on_delete=models.CASCADE, related_name="applications", verbose_name="Dönem")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="board_applications", verbose_name="Üye")

    department = models.CharField(max_length=200, verbose_name="Bölüm")
    grade = models.CharField(max_length=10, choices=Grade.choices, verbose_name="Sınıf")
    phone = models.CharField(max_length=20, verbose_name="Telefon")

    motivation = models.TextField(max_length=3000, verbose_name="Neden katılmak istiyor")
    club_opinion = models.TextField(max_length=3000, verbose_name="Kulübün durumu hakkında")
    project_idea = models.TextField(max_length=3000, blank=True, verbose_name="Proje / fikir")

    # Position kodları, virgülle ayrılmış (ör. "etkinlik,teknik"). SQLite JSON
    # içinde arama yapamadığı için düz metin; 5 sabit kodda yeterli.
    positions = models.CharField(max_length=120, verbose_name="Pozisyonlar")
    experience = models.TextField(max_length=3000, blank=True, verbose_name="Deneyim")
    weekly_hours = models.CharField(max_length=10, choices=WeeklyHours.choices, verbose_name="Haftalık süre")
    portfolio = models.TextField(max_length=1000, blank=True, verbose_name="Portfolyo linkleri")
    extra = models.TextField(max_length=3000, blank=True, verbose_name="Eklemek istedikleri")

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, verbose_name="Durum")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Yönetim kurulu başvurusu"
        verbose_name_plural = "Yönetim kurulu başvuruları"
        constraints = [
            models.UniqueConstraint(fields=["round", "user"], name="one_board_application_per_round"),
        ]

    def __str__(self):
        return f"{self.user} — {self.round}"

    @property
    def position_labels(self):
        etiketler = dict(self.Position.choices)
        return [etiketler.get(kod, kod) for kod in self.positions.split(",") if kod]

    @property
    def portfolio_links(self):
        """Her satır bir link. Yalnızca http(s) adresleri tıklanabilir olur; aday
        "javascript:..." yazsa bile karargahta çalıştırılabilir bir link oluşmaz."""
        linkler = []
        for satir in self.portfolio.splitlines():
            metin = satir.strip()
            if metin:
                guvenli = metin.lower().startswith(("http://", "https://"))
                linkler.append({"text": metin, "url": metin if guvenli else None})
        return linkler

from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from core.crypto import (
    encrypt_value,
    decrypt_value,
    hash_national_id,
    is_encrypted,
    is_valid_national_id,
)
class GameJam(TimeStampedModel):
    event = models.OneToOneField(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="jam",
        limit_choices_to={"event_type": "game_jam"},
    )
    application_deadline  = models.DateTimeField(verbose_name="Başvuru Bitiş Tarihi")
    max_team_size         = models.PositiveSmallIntegerField(default=5, verbose_name="Maksimum Takım Boyutu")

    # Her jam'de değişebilecek roller — JSON formatında
    # Örnek: ["Developer", "3D Artist", "2D Artist", "Game Designer", "Sound Designer"]
    available_roles = models.JSONField(default=list, blank=True, verbose_name="Açık Roller")

    # Her jam'de değişen sorular — JSON formatında
    custom_questions = models.JSONField(default=list, blank=True, verbose_name="Özel Sorular")

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Game Jam"
        verbose_name_plural = "Game Jam'ler"

    def __str__(self):
        return f"{self.event.title} - Jam Detayları"


class SuggestedTeam(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING  = "pending",  "Onay Bekliyor"
        APPROVED = "approved", "Onaylandı"
        REJECTED = "rejected", "Reddedildi"

    jam         = models.ForeignKey(GameJam, on_delete=models.CASCADE, related_name="suggested_teams")
    name        = models.CharField(max_length=100, verbose_name="Takım Adı")
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="Durum")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="İnceleyen"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="İnceleme Tarihi")

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Önerilen Takım"
        verbose_name_plural = "Önerilen Takımlar"

    def __str__(self):
        return f"{self.name} ({self.jam.event.title})"


class JamApplication(TimeStampedModel):
    class TeamStatus(models.TextChoices):
        SOLO    = "solo",     "Solo katılıyorum"
        HAS_TEAM = "has_team", "Ekibim var"
        LOOKING = "looking",  "Ekip arıyorum"

    class ApplicationStatus(models.TextChoices):
        PENDING  = "pending",  "Beklemede"
        APPROVED = "approved", "Onaylandı"
        REJECTED = "rejected", "Reddedildi"

    jam       = models.ForeignKey(GameJam, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="jam_applications",
    )

    # ── Sabit Alanlar ──
    full_name        = models.CharField(max_length=200, verbose_name="Ad Soyad")
    birth_date       = models.DateField(null=True, blank=True, verbose_name="Doğum Tarihi")
    email            = models.EmailField(verbose_name="E-posta")
    phone_number     = models.CharField(max_length=20, blank=True, verbose_name="Telefon Numarası")
    national_id      = models.CharField(max_length=255, blank=True, verbose_name="T.C. Kimlik Numarası")
    national_id_hash = models.CharField(max_length=64, blank=True, verbose_name="T.C. Kimlik Hash (Gizli)")
    university       = models.CharField(max_length=200, blank=True, verbose_name="Üniversite")
    department       = models.CharField(max_length=200, blank=True, verbose_name="Bölüm")
    grade            = models.CharField(max_length=50, blank=True, verbose_name="Sınıf")
    emergency_contact = models.CharField(max_length=200, blank=True, verbose_name="Acil Durumda Ulaşılacak Kişi ve No")
    health_notes     = models.TextField(blank=True, verbose_name="Kronik Hastalık / Alerji")
    jam_role         = models.CharField(max_length=100, verbose_name="Rol")
    experience_level = models.CharField(max_length=50, blank=True, verbose_name="Deneyim Seviyesi")
    team_status      = models.CharField(max_length=20, choices=TeamStatus.choices, verbose_name="Takım Durumu", db_index=True)
    team_name        = models.CharField(max_length=100, blank=True, verbose_name="Takım Adı")
    portfolio_url    = models.TextField(blank=True, verbose_name="Portfolyo Linkleri")
    previous_jams    = models.TextField(blank=True, verbose_name="Önceki Jam'ler")
    motivation       = models.TextField(blank=True, verbose_name="Motivasyon")
    additional_notes = models.TextField(blank=True, verbose_name="Ek Notlar")
    kvkk_accepted    = models.BooleanField(default=False, verbose_name="KVKK Onayı")
    media_consent    = models.BooleanField(default=False, verbose_name="Fotoğraf/Video Rızası")
    # Sağlık verisi özel nitelikli veridir (KVKK m.6): kendi açık rızası olmadan
    # işlenemez. Rıza yoksa health_notes hiç kaydedilmez.
    health_consent   = models.BooleanField(default=False, verbose_name="Sağlık Verisi Açık Rızası")
    # 6563 sayılı Kanun: etkinlik bilgilendirmesi dışındaki duyurular için gerekli.
    marketing_consent = models.BooleanField(default=False, verbose_name="Ticari Elektronik İleti Onayı")
    # Saklama süresi hesaplamalarında kullanılır (bkz. purge_expired_data komutu).
    health_purged_at = models.DateTimeField(null=True, blank=True, verbose_name="Sağlık Verisi Silinme Tarihi")

    # ── Dinamik Alanlar ──
    custom_answers = models.JSONField(default=dict, blank=True, verbose_name="Özel Cevaplar")

    # ── Durum ve İnceleme ──
    status         = models.CharField(max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.PENDING, verbose_name="Durum", db_index=True)
    reviewer_notes = models.TextField(blank=True, verbose_name="İnceleyen Notları")

    # ── Matchmaker ──
    suggested_team = models.ForeignKey(
        SuggestedTeam,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="members",
        verbose_name="Önerilen Takım"
    )

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Jam Başvurusu"
        verbose_name_plural = "Jam Başvuruları"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["jam", "email"], name="unique_application_per_jam"),
            # Koşul ŞART: T.C. kimliği girilmemiş başvurularda hash '' olur ve
            # koşulsuz kısıt aynı jam'deki ikinci böyle kaydı reddederdi.
            models.UniqueConstraint(
                fields=["jam", "national_id_hash"],
                condition=~models.Q(national_id_hash=""),
                name="unique_national_id_per_jam",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.jam.event.title}"

    def save(self, *args, **kwargs):
        if self.national_id and not is_encrypted(self.national_id):
            if not is_valid_national_id(self.national_id):
                # Biçimsiz bir değer asla düz metin olarak veritabanına yazılmamalı.
                raise ValueError("Geçersiz T.C. Kimlik Numarası biçimi.")
            # Tekillik kontrolü için şifrelemeden bağımsız HMAC özeti.
            self.national_id_hash = hash_national_id(self.national_id)
            self.national_id = encrypt_value(self.national_id)
        super().save(*args, **kwargs)

    @property
    def decrypted_national_id(self):
        if not self.national_id:
            return ""
        try:
            return decrypt_value(self.national_id)
        except Exception:
            return "ŞİFRE ÇÖZÜLEMEDİ"

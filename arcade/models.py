"""
Yılan Oyunu — Veri Modeli
==========================

Competition: admin'den yönetilen yarışma penceresi + aç/kapa anahtarı
             ("Ana sayfada göster"). Stand haftası bitince kutu kaldırılır;
             deploy gerekmez.
GameRun:     tek bir oyunun skoru. Yarışmaya FK ile bağlı DEĞİLDİR; hangi
             yarışmaya sayılacağını created_at zaman damgası belirler.
"""

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel

# 20x20 ızgara, başlangıç uzunluğu 3 → en fazla 400 - 3 = 397 yem.
# static/js/snake.js'teki GRID / START_LEN ile birlikte değişmelidir.
MAX_SCORE = 397

# Üye olmadan oynanan skor, bu süre içinde aynı tarayıcıdan giriş/kayıt
# yapılırsa hesaba bağlanır; sonra purge_expired_data siler.
UNCLAIMED_TTL = timedelta(hours=24)

# Sahipsiz skor kimliklerinin tutulduğu oturum anahtarı.
PENDING_SESSION_KEY = "arcade_pending"


class Competition(TimeStampedModel):
    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Başlamadı"
        LIVE = "live", "Sürüyor"
        ENDED = "ended", "Bitti"

    name = models.CharField(max_length=120, verbose_name="Ad")
    starts_at = models.DateTimeField(verbose_name="Başlangıç")
    ends_at = models.DateTimeField(verbose_name="Bitiş")
    is_visible = models.BooleanField(
        default=False,
        verbose_name="Ana sayfada göster",
        help_text="Açıkken ana sayfada oyun bölümü ve menü bağlantısı görünür. "
                  "Kapatınca oyun tamamen kapanır (API dahil).",
    )

    class Meta:
        ordering = ["-starts_at"]
        verbose_name = "Yarışma"
        verbose_name_plural = "Yarışmalar"

    def __str__(self):
        return self.name

    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "Bitiş, başlangıçtan sonra olmalı."})

    @classmethod
    def current(cls):
        """Ana sayfada gösterilen yarışma; yoksa None (oyun kapalı)."""
        return cls.objects.filter(is_visible=True).order_by("-starts_at").first()

    @property
    def status(self):
        simdi = timezone.now()
        if simdi < self.starts_at:
            return self.Status.UPCOMING
        if simdi > self.ends_at:
            return self.Status.ENDED
        return self.Status.LIVE


class GameRun(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="game_runs",
        verbose_name="Oyuncu",
        help_text="Boşsa skor henüz sahiplenilmemiş (üye olmadan oynanmış).",
    )
    score = models.PositiveIntegerField(verbose_name="Skor")
    duration_ms = models.PositiveIntegerField(verbose_name="Süre (ms)")
    # Biletin tek kullanımlık olmasını veritabanı garanti eder.
    nonce = models.CharField(max_length=32, unique=True, editable=False)
    is_disqualified = models.BooleanField(default=False, verbose_name="Diskalifiye")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Tarih")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Oyun skoru"
        verbose_name_plural = "Oyun skorları"

    def __str__(self):
        return f"Skor {self.score}"

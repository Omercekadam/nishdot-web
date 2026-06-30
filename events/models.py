from django.db import models

from core.models import TimeStampedModel


class Event(TimeStampedModel):
    """
    Tüm etkinliklerin (Game Jam, Workshop, Buluşma, vb.) genel modelidir.
    """
    class EventType(models.TextChoices):
        GAME_JAM  = "game_jam",  "Game Jam"
        WORKSHOP  = "workshop",  "Workshop"
        MEETUP    = "meetup",    "Buluşma"
        TALK      = "talk",      "Konuşma"
        OTHER     = "other",     "Diğer"

    class Status(models.TextChoices):
        DRAFT     = "draft",     "Taslak"
        PUBLISHED = "published", "Yayında"
        COMPLETED = "completed", "Tamamlandı"
        CANCELLED = "cancelled", "İptal Edildi"

    title       = models.CharField(max_length=200, verbose_name="Başlık")
    slug        = models.SlugField(unique=True, verbose_name="URL Slug")
    description = models.TextField(verbose_name="Açıklama")
    event_type  = models.CharField(max_length=20, choices=EventType.choices, verbose_name="Etkinlik Tipi")
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name="Durum")

    start_date  = models.DateTimeField(verbose_name="Başlangıç Tarihi")
    end_date    = models.DateTimeField(verbose_name="Bitiş Tarihi")
    location    = models.CharField(max_length=300, verbose_name="Konum")

    cover_image = models.ImageField(upload_to="events/covers/", blank=True, verbose_name="Kapak Görseli")
    thumbnail   = models.ImageField(upload_to="events/thumbnails/", blank=True, verbose_name="Liste Görseli (Kırpılmış)")

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Etkinlik"
        verbose_name_plural = "Etkinlikler"
        ordering = ["-start_date"]

    def __str__(self):
        return self.title

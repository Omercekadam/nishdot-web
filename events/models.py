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
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name="Durum", db_index=True)

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

    def save(self, *args, **kwargs):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import InMemoryUploadedFile
        import sys
        import os

        # Helper for compressing images
        def compress_image(image_field, max_width=1920):
            if not image_field:
                return image_field

            # Sadece yeni yüklenen dosyaları sıkıştır
            if not hasattr(image_field.file, 'file'):
                return image_field

            img = Image.open(image_field)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Oransal küçültme
            if img.width > max_width:
                output_size = (max_width, int(img.height * (max_width / img.width)))
                img = img.resize(output_size, Image.Resampling.LANCZOS)

            output = BytesIO()
            img.save(output, format='WebP', quality=85, method=6)
            output.seek(0)

            # Dosya adını .webp olarak değiştir
            filename = os.path.splitext(image_field.name)[0] + '.webp'

            return InMemoryUploadedFile(
                output,
                'ImageField',
                filename,
                'image/webp',
                sys.getsizeof(output),
                None
            )

        # Eski görselleri yakalamak için objeyi kontrol edelim
        try:
            old_obj = Event.objects.get(id=self.id)
            if old_obj.cover_image != self.cover_image:
                self.cover_image = compress_image(self.cover_image, max_width=1920)
            if old_obj.thumbnail != self.thumbnail:
                self.thumbnail = compress_image(self.thumbnail, max_width=800)
        except Event.DoesNotExist:
            self.cover_image = compress_image(self.cover_image, max_width=1920)
            self.thumbnail = compress_image(self.thumbnail, max_width=800)

        super().save(*args, **kwargs)

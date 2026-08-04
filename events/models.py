import logging
import uuid
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

logger = logging.getLogger(__name__)


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
    is_applications_open = models.BooleanField(default=True, verbose_name="Başvurular Açık Mı?")
    is_pinned   = models.BooleanField(default=False, db_index=True, verbose_name="Ana Sayfada Sabitle")

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Etkinlik"
        verbose_name_plural = "Etkinlikler"
        ordering = ["-start_date"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        from io import BytesIO
        from PIL import Image, ImageOps
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
            img = ImageOps.exif_transpose(img)
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
                output.getbuffer().nbytes,
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

class Raffle(TimeStampedModel):
    """
    Etkinlikler içinde düzenlenen anlık çekilişleri (giveaway/raffle) temsil eder.
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='raffles', verbose_name="Etkinlik")
    title = models.CharField(max_length=200, verbose_name="Çekiliş Başlığı")
    secret_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Gizli QR ID")
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    
    class Meta:
        verbose_name = "Çekiliş"
        verbose_name_plural = "Çekilişler"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.event.title})"

class RaffleParticipant(models.Model):
    raffle = models.ForeignKey(Raffle, on_delete=models.CASCADE, related_name='participants')
    # Kayıtlı kullanıcılar QR ile katılır; boş bırakılırsa yönetici tarafından
    # elle eklenmiş bir misafir katılımcı olduğu anlamına gelir (bkz. guest_name).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='raffle_participations',
    )
    guest_name = models.CharField(max_length=200, blank=True, verbose_name="Misafir Adı")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Çekiliş Katılımcısı"
        verbose_name_plural = "Çekiliş Katılımcıları"
        # Bir kullanıcı aynı çekilişe sadece bir kez katılabilir. user=NULL olan
        # misafir kayıtları PostgreSQL'de bu kısıtta her zaman farklı sayılır,
        # yani birden fazla misafir aynı çekilişe elle eklenebilir.
        unique_together = ('raffle', 'user')

    def __str__(self):
        return f"{self.display_name} - {self.raffle.title}"

    @property
    def display_name(self):
        if self.user_id:
            return self.user.get_full_name() or self.user.username
        return self.guest_name or "İsimsiz Misafir"

class EventGame(TimeStampedModel):
    """
    Geçmiş Jam veya etkinliklerde üretilen oyunları sergilemek için model.
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='games', verbose_name="Etkinlik")
    title = models.CharField(max_length=200, verbose_name="Oyun Adı")
    url = models.URLField(max_length=500, verbose_name="Oyun Linki (Itch.io vb.)")
    cover_image = models.ImageField(upload_to="events/games/", verbose_name="Kapak Görseli")

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Etkinlik Oyunu"
        verbose_name_plural = "Etkinlik Oyunları"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.event.title})"

    def save(self, *args, **kwargs):
        from io import BytesIO
        from PIL import Image, ImageOps
        from django.core.files.uploadedfile import InMemoryUploadedFile
        import sys
        import os

        # Helper for compressing images
        def compress_image(image_field, max_width=800):
            if not image_field:
                return image_field

            if not hasattr(image_field.file, 'file'):
                return image_field

            img = Image.open(image_field)
            img = ImageOps.exif_transpose(img)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            if img.width > max_width:
                output_size = (max_width, int(img.height * (max_width / img.width)))
                img = img.resize(output_size, Image.Resampling.LANCZOS)

            output = BytesIO()
            img.save(output, format='WebP', quality=85, method=6)
            output.seek(0)

            filename = os.path.splitext(image_field.name)[0] + '.webp'

            return InMemoryUploadedFile(
                output,
                'ImageField',
                filename,
                'image/webp',
                output.getbuffer().nbytes,
                None
            )

        try:
            old_obj = EventGame.objects.get(id=self.id)
            if old_obj.cover_image != self.cover_image:
                self.cover_image = compress_image(self.cover_image, max_width=800)
        except EventGame.DoesNotExist:
            self.cover_image = compress_image(self.cover_image, max_width=800)

        super().save(*args, **kwargs)

class EventApplication(TimeStampedModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="event_applications",
    )
    full_name = models.CharField(max_length=200, verbose_name="Ad Soyad")
    email = models.EmailField(verbose_name="E-posta")
    university = models.CharField(max_length=200, verbose_name="Üniversite")
    department = models.CharField(max_length=200, verbose_name="Bölüm")
    grade = models.CharField(max_length=50, verbose_name="Sınıf")
    is_nisantasi_student = models.BooleanField(default=True, verbose_name="Nişantaşı Öğrencisi mi?")
    national_id = models.CharField(max_length=255, blank=True, verbose_name="T.C. Kimlik Numarası")
    national_id_hash = models.CharField(max_length=64, blank=True, verbose_name="T.C. Kimlik Hash")

    # ── Onaylar (JamApplication ile aynı mantık) ──────────────────────────
    # Aydınlatma metni onayı zorunlu; diğer ikisi açık rızadır ve isteğe bağlıdır.
    kvkk_accepted     = models.BooleanField(default=False, verbose_name="KVKK Onayı")
    media_consent     = models.BooleanField(default=False, verbose_name="Fotoğraf/Video Rızası")
    marketing_consent = models.BooleanField(default=False, verbose_name="Ticari Elektronik İleti Onayı")

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Etkinlik Başvurusu"
        verbose_name_plural = "Etkinlik Başvuruları"

    def __str__(self):
        return f"{self.full_name} - {self.event.title}"

    def save(self, *args, **kwargs):
        # T.C. Kimlik Numarası KVKK gereği asla düz metin saklanmaz —
        # JamApplication ile aynı şifreleme uygulanır.
        if self.national_id and not is_encrypted(self.national_id):
            if not is_valid_national_id(self.national_id):
                raise ValueError("Geçersiz T.C. Kimlik Numarası biçimi.")
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

class EventImage(TimeStampedModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="gallery_images")
    image = models.ImageField(upload_to="events/gallery/", verbose_name="Görsel")
    caption = models.CharField(max_length=255, blank=True, verbose_name="Açıklama")
    
    class Meta(TimeStampedModel.Meta):
        verbose_name = "Etkinlik Görseli"
        verbose_name_plural = "Etkinlik Görselleri"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event.title} - {self.id}"

    def save(self, *args, **kwargs):
        from io import BytesIO
        from PIL import Image, ImageOps
        from django.core.files.uploadedfile import InMemoryUploadedFile
        import sys
        import os

        def compress_image(image_field, max_width=1920):
            if not image_field:
                return image_field

            if not hasattr(image_field.file, 'file'):
                return image_field

            ext = os.path.splitext(image_field.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                return image_field

            try:
                img = Image.open(image_field)
                img = ImageOps.exif_transpose(img)
                if img.mode in ('RGBA', 'P', 'LA'):
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1] if img.mode != 'P' else None)
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                if img.width > max_width:
                    wpercent = (max_width / float(img.width))
                    hsize = int((float(img.height) * float(wpercent)))
                    img = img.resize((max_width, hsize), Image.Resampling.LANCZOS)
                
                output = BytesIO()
                img.save(output, format='JPEG', quality=80, optimize=True)
                output.seek(0)
                
                new_filename = f"{os.path.splitext(os.path.basename(image_field.name))[0]}.jpg"
                return InMemoryUploadedFile(
                    output, 'ImageField', new_filename,
                    'image/jpeg', output.getbuffer().nbytes, None
                )
            except Exception:
                logger.exception("EventImage görsel sıkıştırma başarısız oldu")
                return image_field

        try:
            if self.pk:
                old_obj = EventImage.objects.get(pk=self.pk)
                if old_obj.image != self.image:
                    self.image = compress_image(self.image)
            else:
                self.image = compress_image(self.image)
        except Exception:
            self.image = compress_image(self.image)

        super().save(*args, **kwargs)

from django.db import models
from django.conf import settings

class MeetingNote(models.Model):
    title = models.CharField(max_length=200, verbose_name="Toplantı Başlığı")
    content = models.TextField(verbose_name="Notlar")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Yazar")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Toplantı Notu"
        verbose_name_plural = "Toplantı Notları"

    def __str__(self):
        return self.title

class BoardTask(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "Yapılacaklar"
        IN_PROGRESS = "in_progress", "Sürüyor"
        DONE = "done", "Bitti"

    class Priority(models.TextChoices):
        LOW = "low", "Düşük"
        MEDIUM = "medium", "Orta"
        HIGH = "high", "Yüksek"
        URGENT = "urgent", "Acil"
        
    class Category(models.TextChoices):
        ADMIN = "admin", "Yönetim"
        EVENT = "event", "Etkinlik"
        DESIGN = "design", "Tasarım"
        TECH = "tech", "Teknik"
        SOCIAL = "social", "Sosyal Medya"

    title = models.CharField(max_length=200, verbose_name="Görev Adı")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks", verbose_name="Atanan Kişi")
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_tasks", verbose_name="Oluşturan")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO, verbose_name="Durum")
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM, verbose_name="Öncelik")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.ADMIN, verbose_name="Kategori")
    deadline = models.DateTimeField(null=True, blank=True, verbose_name="Son Teslim Tarihi (Deadline)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Yönetim Görevi"
        verbose_name_plural = "Yönetim Görevleri"

    def __str__(self):
        return self.title

class ClubAsset(models.Model):
    class AssetType(models.TextChoices):
        FINANCE_IN = "income", "Gelir (Kasa)"
        FINANCE_OUT = "expense", "Gider (Kasa)"
        EQUIPMENT = "equipment", "Demirbaş / Eşya"

    type = models.CharField(max_length=20, choices=AssetType.choices, verbose_name="Tür")
    title = models.CharField(max_length=200, verbose_name="Başlık (Örn: VR Gözlük veya Pizza)")
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Tutar (TL)")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Adet")
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Zimmetli Kişi")
    notes = models.TextField(blank=True, verbose_name="Notlar")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kulüp Varlığı"
        verbose_name_plural = "Kulüp Varlıkları"

    def __str__(self):
        return self.title

class Announcement(models.Model):
    title = models.CharField(max_length=200, verbose_name="Başlık")
    content = models.TextField(verbose_name="İçerik")
    published_to_site = models.BooleanField(default=False)
    published_to_discord = models.BooleanField(default=False)
    sent_via_email = models.BooleanField(default=False)
    
    target_audience = models.CharField(max_length=20, default='all', verbose_name="Hedef Kitle")
    custom_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='custom_announcements', verbose_name="Özel Alıcılar")
    dismissed_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='dismissed_announcements', verbose_name="Gizleyen Kullanıcılar")
    
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Duyuru"
        verbose_name_plural = "Duyurular"

    def __str__(self):
        return self.title
